"""Automatic FBIL rate backfill for the rates-display path.

When a user views a date range that has a sizable hole in the DB, this fetches
that stretch straight from FBIL and seeds it — so missing data self-heals with
no manual step. Read + insert only: it never edits existing rows or the
matching logic. Returns a layman notice explaining what happened (or why not).
"""
from datetime import date, datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models import FBILRate
from services.fbil_scraper import fetch_fbil_rates
import logging

logger = logging.getLogger(__name__)

FBIL_START = date(2018, 7, 10)   # FBIL publishes nothing before this
# A genuine "missing seed" hole. Normal weekend+holiday clusters are <=~5 days,
# so >=8 consecutive missing days means the data was never seeded, not a holiday.
MIN_GAP_DAYS = 8

# Ranges already attempted this process lifetime — avoids re-hitting FBIL for a
# stretch it simply doesn't publish (e.g. a long holiday cluster).
_attempted: set = set()


async def fill_missing_range(db: AsyncSession, from_date: date, to_date: date) -> dict:
    """Detect + seed sizable missing stretches inside [from_date, to_date].
    Returns {"added": int, "notice": str}."""
    today = datetime.utcnow().date()

    if to_date < FBIL_START:
        return {"added": 0, "notice": "FBIL publishes rates from 10 Jul 2018 onward — earlier dates aren't available."}
    if from_date > today:
        return {"added": 0, "notice": "Selected dates are in the future — FBIL hasn't published these rates yet."}

    lo = max(from_date, FBIL_START)
    hi = min(to_date, today)
    if lo > hi:
        return {"added": 0, "notice": ""}

    res = await db.execute(
        select(FBILRate.date).where(and_(FBILRate.date >= lo, FBILRate.date <= hi)).distinct()
    )
    present = {r[0] for r in res.all()}

    # Walk the range and collect contiguous missing stretches
    missing, gap_start, one = [], None, timedelta(days=1)
    d = lo
    while d <= hi:
        if d not in present:
            if gap_start is None:
                gap_start = d
        elif gap_start is not None:
            missing.append((gap_start, d - one))
            gap_start = None
        d += one
    if gap_start is not None:
        missing.append((gap_start, hi))

    holes = [(a, b) for (a, b) in missing if (b - a).days + 1 >= MIN_GAP_DAYS]
    if not holes:
        return {"added": 0, "notice": ""}

    added = 0
    fbil_reached = True
    for (a, b) in holes:
        key = (a, b)
        if key in _attempted:
            continue
        _attempted.add(key)

        r2 = await db.execute(
            select(FBILRate.date, FBILRate.currency_pair).where(and_(FBILRate.date >= a, FBILRate.date <= b))
        )
        existing = {(x[0], x[1]) for x in r2.all()}

        cur = a
        while cur <= b:
            chunk_end = min(cur + timedelta(days=90), b)
            try:
                rows = await fetch_fbil_rates(cur, chunk_end)
            except Exception as e:
                logger.warning(f"rate autofill fetch failed {cur}..{chunk_end}: {e}")
                rows, fbil_reached = [], False
            for row in rows:
                k = (row["date"], row["currency_pair"])
                if k in existing:
                    continue
                db.add(FBILRate(
                    date=row["date"], time=row.get("time"),
                    currency_pair=row["currency_pair"], rate=row["rate"],
                    comments=row.get("comments"),
                ))
                existing.add(k)
                added += 1
            cur = chunk_end + timedelta(days=1)

    if added:
        await db.commit()
        return {"added": added, "notice": f"Fetched {added} missing rates from FBIL for this range."}
    if not fbil_reached:
        return {"added": 0, "notice": "Couldn't reach FBIL to fetch the missing dates — showing available data."}
    return {"added": 0, "notice": "No FBIL rates exist for the missing days in this range (likely holidays/weekends)."}
