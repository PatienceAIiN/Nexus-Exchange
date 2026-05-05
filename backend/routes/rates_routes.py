from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import get_db
from models import FBILRate, User
from auth import get_current_user
from typing import Optional, List
from datetime import date, timedelta
import io
import pandas as pd
from config import settings

router = APIRouter(prefix="/api/rates", tags=["rates"])

# WebSocket manager (shared with main.py)
ws_manager = None

def set_ws_manager(manager):
    global ws_manager
    ws_manager = manager

@router.get("")
async def get_rates(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    currency_pair: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not from_date:
        from_date = date.today() - timedelta(days=30)
    if not to_date:
        to_date = date.today()

    conditions = [FBILRate.date >= from_date, FBILRate.date <= to_date]
    if currency_pair and currency_pair != "all":
        conditions.append(FBILRate.currency_pair == currency_pair)

    query = select(FBILRate).where(and_(*conditions)).order_by(FBILRate.date.desc(), FBILRate.currency_pair)
    result = await db.execute(query)
    all_rates = result.scalars().all()

    total = len(all_rates)
    start = (page - 1) * per_page
    paginated = all_rates[start:start + per_page]

    return {
        "data": [{"id": r.id, "date": str(r.date), "time": r.time, "currency_pair": r.currency_pair,
                  "rate": r.rate, "comments": r.comments} for r in paginated],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }

@router.get("/latest")
async def get_latest_rates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get latest date with data
    result = await db.execute(select(FBILRate).order_by(FBILRate.date.desc()).limit(6))
    rates = result.scalars().all()
    return [{"id": r.id, "date": str(r.date), "time": r.time, "currency_pair": r.currency_pair,
             "rate": r.rate, "comments": r.comments} for r in rates]

@router.post("/refresh")
async def refresh_rates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.fbil_scraper import scrape_latest_rates
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    try:
        rows = await scrape_latest_rates()
        if rows:
            for row in rows:
                existing = await db.execute(
                    select(FBILRate).where(
                        and_(FBILRate.date == row["date"], FBILRate.currency_pair == row["currency_pair"])
                    )
                )
                existing_rate = existing.scalar_one_or_none()
                if existing_rate:
                    existing_rate.rate = row["rate"]
                    existing_rate.time = row.get("time")
                else:
                    db.add(FBILRate(**row))
            await db.commit()

        # Broadcast via WebSocket
        if ws_manager:
            await ws_manager.broadcast({"event": "rates_updated", "count": len(rows)})

        return {"message": f"Refreshed {len(rows)} rate entries"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
async def download_rates(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    format: str = Query("csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not from_date:
        from_date = date.today() - timedelta(days=30)
    if not to_date:
        to_date = date.today()

    result = await db.execute(
        select(FBILRate).where(
            and_(FBILRate.date >= from_date, FBILRate.date <= to_date)
        ).order_by(FBILRate.date.desc())
    )
    rates = result.scalars().all()

    df = pd.DataFrame([{
        "Date": r.date.strftime("%d %b %Y"),
        "Time": r.time or "",
        "Currency Pairs": r.currency_pair,
        "Rate": r.rate,
        "Comments": r.comments or "",
    } for r in rates])

    if format == "csv":
        output = io.StringIO()
        output.write("Financial Benchmarks India Pvt Ltd\nReference Rates\n")
        df.to_csv(output, index=False)
        content = output.getvalue().encode()
        media_type = "text/csv"
        ext = "csv"
    elif format == "xlsx":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="FBIL Rates")
            ws = writer.sheets["FBIL Rates"]
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 20
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    elif format == "pdf":
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elements = []
        elements.append(Paragraph("FBIL Reference Rates", styles["Title"]))
        elements.append(Paragraph(f"Period: {from_date} to {to_date}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        table_data = [["Date", "Time", "Currency Pair", "Rate", "Comments"]]
        for r in rates:
            table_data.append([r.date.strftime("%d %b %Y"), r.time or "", r.currency_pair, str(r.rate), r.comments or ""])

        t = Table(table_data)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2035")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elements.append(t)
        doc.build(elements)
        content = output.getvalue()
        media_type = "application/pdf"
        ext = "pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid format")

    filename = f"fbil_rates_{from_date}_{to_date}.{ext}"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
