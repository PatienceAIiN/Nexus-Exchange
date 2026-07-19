from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import get_db
from models import FBILRate, ProcessedFile, User
from auth import get_current_user
from config import settings
from services.file_processor import process_expense_file, convert_processed
from services import r2_storage
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import uuid
import io
from datetime import datetime, timedelta, date
import logging

router = APIRouter(prefix="/api/processing", tags=["processing"])
logger = logging.getLogger(__name__)

# In-memory task progress store
task_progress: dict = {}


async def _backfill_missing_rates(db: AsyncSession, unmatched_dates: list) -> int:
    """Auto-heal: when an uploaded file references dates that have no FBIL rate
    in the DB, fetch that date range straight from FBIL and seed it. Returns the
    number of rows added. This only reads from FBIL and inserts new rows — it
    never touches the matching logic or existing rows."""
    from services.fbil_scraper import fetch_fbil_rates

    parsed = []
    for s in unmatched_dates:
        try:
            parsed.append(datetime.strptime(str(s)[:10], "%Y-%m-%d").date())
        except Exception:
            continue
    if not parsed:
        return 0

    fbil_start = date(2018, 7, 10)          # FBIL publishes nothing before this
    today = datetime.utcnow().date()
    fetch_from = max(min(parsed) - timedelta(days=10), fbil_start)  # pad for holiday look-back
    fetch_to = min(max(parsed), today)
    if fetch_from > fetch_to:
        return 0

    added = 0
    cur = fetch_from
    while cur <= fetch_to:                    # FBIL likes <=90-day windows
        chunk_end = min(cur + timedelta(days=90), fetch_to)
        rows = await fetch_fbil_rates(cur, chunk_end)
        if rows:
            # Dedup against the ACTUAL dates FBIL returned so an out-of-window
            # row can never create a duplicate.
            cand_dates = {r["date"] for r in rows}
            ex = await db.execute(
                select(FBILRate.date, FBILRate.currency_pair).where(FBILRate.date.in_(cand_dates))
            )
            have = {(x[0], x[1]) for x in ex.all()}
            for r in rows:
                key = (r["date"], r["currency_pair"])
                if key in have:
                    continue
                db.add(FBILRate(
                    date=r["date"], time=r.get("time"),
                    currency_pair=r["currency_pair"], rate=r["rate"],
                    comments=r.get("comments"),
                ))
                have.add(key)
                added += 1
        cur = chunk_end + timedelta(days=1)

    if added:
        await db.commit()
    logger.info(f"Auto-backfill: added {added} FBIL rates for {fetch_from}..{fetch_to}")
    return added

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

        # Auto-heal: if any dates had no FBIL rate in the DB, fetch that range
        # from FBIL, seed it, and reprocess ONCE. Wrapped so any failure (FBIL
        # down, etc.) silently keeps the original first-pass result unchanged.
        auto_seeded = 0
        if stats.get("unmatched_rows", 0) > 0 and stats.get("unmatched_dates"):
            try:
                auto_seeded = await _backfill_missing_rates(db, stats["unmatched_dates"])
                if auto_seeded > 0:
                    res2 = await db.execute(select(FBILRate))
                    rates_rows = res2.scalars().all()
                    processed_bytes, stats = await process_expense_file(
                        file_bytes, file.filename, rates_rows, update_progress
                    )
            except Exception as e:
                logger.warning(f"Auto-backfill skipped (kept original result): {e}")

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
            "message": (
                f"Done! {stats['matched_rows']}/{stats['total_rows']} rows matched."
                + (f" Auto-fetched {auto_seeded} missing FBIL rates." if auto_seeded else "")
            ),
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
    format: str = Query(default="", description="Download format: xlsx | csv | pdf"),
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

    fmt = (format or "").strip().lower()
    if fmt and fmt not in ("xlsx", "csv", "pdf", "excel"):
        raise HTTPException(status_code=400, detail="Unsupported format. Use xlsx, csv or pdf.")

    try:
        file_bytes = r2_storage.download_file(record.r2_processed_key)
        out_bytes, media_type, ext = convert_processed(file_bytes, record.processed_filename, fmt)
        base = (record.original_filename or record.processed_filename or "processed").rsplit(".", 1)[0]
        out_name = f"{base}_processed.{ext}"
        return StreamingResponse(
            io.BytesIO(out_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
        )
    except Exception as e:
        logger.error(f"Download/convert failed for file {file_id} fmt={fmt}: {e}", exc_info=True)
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
