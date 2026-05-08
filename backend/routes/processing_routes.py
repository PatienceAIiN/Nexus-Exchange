from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import get_db
from models import FBILRate, ProcessedFile, User
from auth import get_current_user
from config import settings
from services.file_processor import process_expense_file
from services import r2_storage
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import uuid
import io
from datetime import datetime
import logging

router = APIRouter(prefix="/api/processing", tags=["processing"])
logger = logging.getLogger(__name__)

# In-memory task progress store
task_progress: dict = {}

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith((".xlsx", ".csv")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .csv files are accepted")

    file_bytes = await file.read()
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB}MB")

    # Fetch all rates upfront for matching
    result = await db.execute(select(FBILRate))
    rates_rows = result.scalars().all()

    async def update_progress(pct: int, stage: str, message: str):
        pass

    try:
        # Upload original to R2
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        original_key = f"originals/{current_user.id}/{timestamp}_{file.filename}"
        try:
            r2_storage.upload_file(file_bytes, original_key)
        except Exception as e:
            logger.warning(f"R2 upload failed: {e}")
            original_key = None

        processed_bytes, stats = await process_expense_file(
            file_bytes, file.filename, rates_rows, update_progress
        )

        # Upload processed file to R2
        processed_filename = f"processed_{file.filename}"
        processed_key = f"processed/{current_user.id}/{timestamp}_{processed_filename}"
        download_url = None
        try:
            r2_storage.upload_file(processed_bytes, processed_key)
            download_url = r2_storage.generate_presigned_url(processed_key)
        except Exception as e:
            logger.warning(f"R2 processed upload failed: {e}")
            processed_key = None

        # Save to DB
        record = ProcessedFile(
            user_id=current_user.id,
            original_filename=file.filename,
            processed_filename=processed_filename,
            r2_original_key=original_key,
            r2_processed_key=processed_key,
            total_rows=stats["total_rows"],
            matched_rows=stats["matched_rows"],
            unmatched_rows=stats["unmatched_rows"],
            status="completed",
            processing_log=json.dumps(stats),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        return {
            "done": True,
            "message": f"Done! {stats['matched_rows']}/{stats['total_rows']} rows matched.",
            "stats": stats,
            "file_id": record.id,
            "download_url": download_url
        }

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress/{task_id}")
async def get_progress(task_id: str, current_user: User = Depends(get_current_user)):
    async def event_generator():
        last_state = None
        timeout = 300  # 5 minutes max
        elapsed = 0
        while elapsed < timeout:
            state = task_progress.get(task_id)
            if state and state != last_state:
                payload = {k: v for k, v in state.items() if k != "processed_bytes"}
                yield {"data": json.dumps(payload)}
                last_state = dict(state)
                if state.get("done"):
                    break
            await asyncio.sleep(0.5)
            elapsed += 0.5

    return EventSourceResponse(event_generator())

@router.get("/history")
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProcessedFile)
        .where(ProcessedFile.user_id == current_user.id)
        .order_by(ProcessedFile.created_at.desc())
    )
    files = result.scalars().all()
    return [
        {
            "id": f.id,
            "original_filename": f.original_filename,
            "processed_filename": f.processed_filename,
            "total_rows": f.total_rows,
            "matched_rows": f.matched_rows,
            "unmatched_rows": f.unmatched_rows,
            "status": f.status,
            "created_at": str(f.created_at),
            "r2_processed_key": f.r2_processed_key,
        }
        for f in files
    ]

@router.get("/download/{file_id}")
async def download_processed(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProcessedFile).where(
            and_(ProcessedFile.id == file_id, ProcessedFile.user_id == current_user.id)
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if not record.r2_processed_key:
        raise HTTPException(status_code=404, detail="Processed file not available")

    try:
        file_bytes = r2_storage.download_file(record.r2_processed_key)
        ext = record.processed_filename.split(".")[-1].lower()
        media_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
        }
        media_type = media_types.get(ext, "application/octet-stream")
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{record.processed_filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.delete("/file/{file_id}")
async def delete_processed_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProcessedFile).where(
            and_(ProcessedFile.id == file_id, ProcessedFile.user_id == current_user.id)
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        if record.r2_original_key:
            r2_storage.delete_file(record.r2_original_key)
    except Exception as e:
        logger.warning(f"Failed to delete original file from R2: {e}")

    try:
        if record.r2_processed_key:
            r2_storage.delete_file(record.r2_processed_key)
    except Exception as e:
        logger.warning(f"Failed to delete processed file from R2: {e}")

    await db.delete(record)
    await db.commit()
    return {"message": "File deleted successfully"}

from pydantic import BaseModel
class BulkDeleteRequest(BaseModel):
    file_ids: list[int]

@router.post("/files/bulk-delete")
async def bulk_delete_processed_files(
    req: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProcessedFile).where(
            and_(ProcessedFile.id.in_(req.file_ids), ProcessedFile.user_id == current_user.id)
        )
    )
    records = result.scalars().all()
    
    if not records:
        return {"message": "No valid files found"}
        
    for record in records:
        try:
            if record.r2_original_key:
                r2_storage.delete_file(record.r2_original_key)
        except: pass
        try:
            if record.r2_processed_key:
                r2_storage.delete_file(record.r2_processed_key)
        except: pass
        await db.delete(record)
        
    await db.commit()
    return {"message": f"{len(records)} files deleted successfully"}
