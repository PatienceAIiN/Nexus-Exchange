import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from io import BytesIO
from datetime import date, timedelta
import json
import httpx
import logging
import re
from services.rate_matcher import find_rate, build_rates_lookup, CURRENCY_MAP
from config import settings

logger = logging.getLogger(__name__)
PRODUCT_FOOTER_TEXT = "Nexus Exchange | A product of Patience AI | https://patienceai.in"


async def detect_columns_with_ai(columns: list, sample_rows: list) -> dict:
    prompt = f"""Given these spreadsheet columns and sample data, identify:
- date_col: column containing transaction/expense date
- currency_col: column containing 3-letter currency code like USD, INR, EUR
- amount_col: column containing amount/value
- ref_rate_col: column for reference/exchange rate (may be empty)

Columns: {columns}
Sample data (first 5 rows): {json.dumps(sample_rows, default=str)}

Return ONLY valid JSON:
{{"date_col": "column_name_or_null", "currency_col": "column_name_or_null", "amount_col": "column_name_or_null", "ref_rate_col": "column_name_or_null"}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                }
            )
            result = resp.json()
            content = result["choices"][0]["message"]["content"].strip()
            json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        logger.error(f"AI column detection failed: {e}")

    return {"date_col": None, "currency_col": None, "amount_col": None, "ref_rate_col": None}

def detect_columns(df: pd.DataFrame) -> dict:
    cols_lower = {str(c).strip().lower(): str(c).strip() for c in df.columns}
    result = {}

    for key in ["expense date", "date", "transaction date", "invoice date", "exp date"]:
        if key in cols_lower:
            result["date_col"] = cols_lower[key]
            break

    for key in ["currency", "currency type", "curr", "ccy"]:
        if key in cols_lower:
            result["currency_col"] = cols_lower[key]
            break

    for key in ["amount", "original amount", "value", "amt"]:
        if key in cols_lower:
            result["amount_col"] = cols_lower[key]
            break

    for key in ["ref rate", "ref_rate", "reference rate", "exchange rate", "fx rate", "refrate"]:
        if key in cols_lower:
            result["ref_rate_col"] = cols_lower[key]
            break

    return result


def _parse_date(raw_date) -> date | None:
    if pd.isna(raw_date) if hasattr(raw_date, '__class__') else raw_date is None:
        return None
    try:
        if isinstance(raw_date, (int, float)):
            # Excel serial date (days since 1899-12-30)
            return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(raw_date))).date()
        if hasattr(raw_date, 'date'):
            return raw_date.date()
        return pd.to_datetime(str(raw_date)).date()
    except Exception:
        return None


async def process_expense_file(
    file_bytes: bytes,
    filename: str,
    rates_rows: list,
    progress_callback=None
) -> tuple[bytes, dict]:
    """
    Process an expense file filling in FBIL reference rates.
    Returns (processed_bytes, stats_dict)
    """
    is_xlsx = filename.lower().endswith(".xlsx")
    rates_lookup = build_rates_lookup(rates_rows)

    if progress_callback:
        await progress_callback(10, "reading", "Reading uploaded file...")

    # ── Step 1: Detect header row ──────────────────────────────────────────
    if is_xlsx:
        df_raw = pd.read_excel(BytesIO(file_bytes), header=None)
    else:
        df_raw = pd.read_csv(BytesIO(file_bytes), header=None)

    header_row_idx = 0
    for i, row in df_raw.iterrows():
        non_null = row.dropna()
        str_cells = [str(v).strip() for v in non_null if str(v).strip()]
        if len(str_cells) >= 3:
            header_row_idx = int(i)
            break

    logger.info(f"Detected header at row {header_row_idx}")

    if is_xlsx:
        df = pd.read_excel(BytesIO(file_bytes), header=header_row_idx)
    else:
        df = pd.read_csv(BytesIO(file_bytes), header=header_row_idx)

    df.columns = [str(c).strip() for c in df.columns]
    # Drop completely empty rows
    df = df.dropna(how="all").reset_index(drop=True)

    if progress_callback:
        await progress_callback(20, "detecting", "Detecting column structure...")

    # ── Step 2: Detect columns ─────────────────────────────────────────────
    col_map = detect_columns(df)

    if not col_map.get("date_col") or not col_map.get("currency_col"):
        sample = df.head(5).to_dict(orient="records")
        logger.info("Heuristic detection failed, trying fallback AI...")
        ai_result2 = await detect_columns_with_ai(list(df.columns), sample)
        for k, v in ai_result2.items():
            if v and str(v) in df.columns and k not in col_map:
                col_map[k] = str(v)

    date_col = col_map.get("date_col")
    currency_col = col_map.get("currency_col")
    ref_rate_col = col_map.get("ref_rate_col") or "Ref Rate"

    logger.info(f"Columns: date={date_col}, currency={currency_col}, ref_rate={ref_rate_col}")

    if not date_col or not currency_col:
        raise ValueError(f"Cannot find date/currency columns. Found: {list(df.columns)}")

    # Add ref rate column if missing
    if ref_rate_col not in df.columns:
        df[ref_rate_col] = None

    if progress_callback:
        await progress_callback(35, "matching", "Matching FBIL rates to expense rows...")

    # ── Step 3: Match rates ────────────────────────────────────────────────
    total_rows = 0
    matched_rows = 0
    unmatched_rows = 0
    unmatched_dates = []

    for idx in range(len(df)):
        row = df.iloc[idx]
        currency_val = str(row.get(currency_col, "")).strip().upper()

        # Skip domestic INR and empty rows
        if not currency_val or currency_val in ("INR", "NAN", "", "NONE", "NAT"):
            continue

        total_rows += 1

        parsed_date = _parse_date(row.get(date_col))

        if parsed_date is None:
            unmatched_rows += 1
            unmatched_dates.append(str(row.get(date_col, "?")))
            continue

        # Emit progress every 30 rows
        if total_rows % 30 == 0 and progress_callback:
            pct = 35 + min(40, int((idx / max(len(df), 1)) * 40))
            await progress_callback(pct, "matching", f"Matching rates: {matched_rows}/{total_rows} rows...")

        rate = find_rate(parsed_date, currency_val, rates_lookup)
        if rate is not None:
            df.at[idx, ref_rate_col] = rate
            matched_rows += 1
        else:
            unmatched_rows += 1
            unmatched_dates.append(str(parsed_date))

    if progress_callback:
        await progress_callback(78, "writing", "Writing processed file preserving formatting...")

    # ── Step 4: Write output ───────────────────────────────────────────────
    if is_xlsx:
        processed_bytes = _write_xlsx(file_bytes, df, header_row_idx, ref_rate_col)
    else:
        out = BytesIO()
        df.to_csv(out, index=False)
        out.write(f"\n\n{PRODUCT_FOOTER_TEXT}\n".encode("utf-8"))
        processed_bytes = out.getvalue()

    if progress_callback:
        await progress_callback(92, "uploading", "Uploading to cloud storage...")

    stats = {
        "total_rows": total_rows,
        "matched_rows": matched_rows,
        "unmatched_rows": unmatched_rows,
        "unmatched_dates": sorted(set(unmatched_dates))[:30],
        "date_col": date_col,
        "currency_col": currency_col,
        "ref_rate_col": ref_rate_col,
        "match_rate_pct": round(matched_rows / max(total_rows, 1) * 100, 1),
    }

    return processed_bytes, stats


def _write_xlsx(original_bytes: bytes, df: pd.DataFrame, header_row_idx: int, ref_rate_col: str) -> bytes:
    """Write processed XLSX preserving original formatting, filling ref rate column."""
    try:
        wb = load_workbook(BytesIO(original_bytes))
        ws = wb.active

        # openpyxl is 1-indexed; header is at header_row_idx+1
        header_ws_row = header_row_idx + 1

        # Find the ref rate column index in the worksheet
        ref_col_idx = None
        for cell in ws[header_ws_row]:
            if cell.value and str(cell.value).strip() == ref_rate_col:
                ref_col_idx = cell.column
                break

        if ref_col_idx is None:
            # Append as new column
            max_col = ws.max_column
            ref_col_idx = max_col + 1
            header_cell = ws.cell(row=header_ws_row, column=ref_col_idx, value=ref_rate_col)
            header_cell.font = Font(bold=True, color="000000")
            header_cell.fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        # Map df index to worksheet row
        # df row 0 → ws row header_ws_row+1
        for df_idx in range(len(df)):
            ws_row = header_ws_row + 1 + df_idx
            if ws_row > ws.max_row:
                break

            rate_val = df.iloc[df_idx].get(ref_rate_col)
            if rate_val is not None and str(rate_val) not in ("nan", "None", ""):
                try:
                    cell = ws.cell(row=ws_row, column=ref_col_idx, value=float(rate_val))
                    cell.number_format = '0.0000'
                except Exception:
                    pass

        out = BytesIO()
        footer_row = header_ws_row + 1 + len(df) + 2
        footer_cell = ws.cell(row=footer_row, column=1, value="Nexus Exchange")
        footer_cell.font = Font(bold=True, color="FFFFFF")
        footer_cell.fill = PatternFill(start_color="1A2035", end_color="1A2035", fill_type="solid")
        footer_cell.alignment = Alignment(horizontal="left")

        company_cell = ws.cell(row=footer_row + 1, column=1, value="A product of Patience AI")
        company_cell.font = Font(color="0B6E4F", bold=True)
        link_cell = ws.cell(row=footer_row + 2, column=1, value="https://patienceai.in")
        link_cell.hyperlink = "https://patienceai.in"
        link_cell.style = "Hyperlink"

        wb.save(out)
        return out.getvalue()

    except Exception as e:
        logger.error(f"openpyxl write error: {e}, falling back to pandas")
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return out.getvalue()
