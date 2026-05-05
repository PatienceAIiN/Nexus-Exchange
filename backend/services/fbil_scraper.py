import httpx
from datetime import date, timedelta, datetime
import logging

logger = logging.getLogger(__name__)

FBIL_API_BASE = "https://www.fbil.org.in/wasdm"

FBIL_CURRENCIES = [
    "INR / 1 USD",
    "INR / 1 GBP",
    "INR / 1 EUR",
    "INR / 100 JPY",
    "INR / 1 AED",
    "INR / 10000 IDR",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, */*",
    "Origin": "https://www.fbil.org.in",
    "Referer": "https://www.fbil.org.in/benchmark/reference",
}


def _parse_row(item: dict) -> dict | None:
    """Parse a single FBIL API response item into our DB format."""
    try:
        raw_date = item.get("processRunDate", "")
        raw_time = item.get("displayTime", "")
        currency_pair = item.get("subProdName", "")
        rate = float(item.get("rate", 0))
        comments = item.get("comments", "") or ""

        if not raw_date or not currency_pair or currency_pair not in FBIL_CURRENCIES:
            return None

        # Parse date: "2026-04-27 00:00:00"
        parsed_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()

        # Parse display time as time string
        time_str = raw_time[11:19] if len(raw_time) >= 19 else raw_time

        return {
            "date": parsed_date,
            "time": time_str,
            "currency_pair": currency_pair,
            "rate": rate,
            "comments": comments,
        }
    except Exception as e:
        logger.debug(f"Row parse error: {e} | item={item}")
        return None


async def fetch_fbil_rates(from_date: date, to_date: date) -> list[dict]:
    """Fetch FBIL reference rates for a date range using the real FBIL API."""
    params = {
        "authenticated": "false",
        "fromDate": from_date.strftime("%Y-%m-%d"),
        "toDate": to_date.strftime("%Y-%m-%d"),
    }

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(
                f"{FBIL_API_BASE}/refrates/fetchfiltered",
                params=params,
                headers=HEADERS,
            )

            if resp.status_code != 200:
                logger.warning(f"FBIL API returned {resp.status_code} for {from_date}–{to_date}")
                # Fallback: try fetch (returns latest only)
                resp2 = await client.get(
                    f"{FBIL_API_BASE}/refrates/fetch",
                    params={"authenticated": "false"},
                    headers=HEADERS,
                )
                if resp2.status_code == 200:
                    data = resp2.json()
                else:
                    return []
            else:
                data = resp.json()

            if not isinstance(data, list):
                logger.error(f"Unexpected FBIL response type: {type(data)}")
                return []

            results = []
            for item in data:
                parsed = _parse_row(item)
                if parsed:
                    results.append(parsed)

            logger.info(f"Fetched {len(results)} rate records from FBIL ({from_date} to {to_date})")
            return results

    except Exception as e:
        logger.error(f"FBIL fetch error: {e}", exc_info=True)
        return []


async def scrape_latest_rates() -> list[dict]:
    """Scrape the most recent FBIL rates (last 7 days to catch weekends)."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    return await fetch_fbil_rates(week_ago, today)


async def scrape_historical_rates(days: int = 730) -> list[dict]:
    """Scrape historical FBIL rates for the past N days, in 90-day chunks."""
    today = date.today()
    from_date = today - timedelta(days=days)

    all_results = []
    chunk_days = 90
    current = from_date

    while current <= today:
        end = min(current + timedelta(days=chunk_days), today)
        logger.info(f"Fetching FBIL chunk: {current} → {end}")
        chunk = await fetch_fbil_rates(current, end)
        all_results.extend(chunk)
        current = end + timedelta(days=1)

    logger.info(f"Historical backfill complete: {len(all_results)} records total")
    return all_results
