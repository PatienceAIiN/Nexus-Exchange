from datetime import date, timedelta
from typing import Optional
import pandas as pd

CURRENCY_MAP = {
    "USD": "INR / 1 USD",
    "GBP": "INR / 1 GBP",
    "EUR": "INR / 1 EUR",
    "JPY": "INR / 100 JPY",
    "AED": "INR / 1 AED",
    "IDR": "INR / 10000 IDR",
}

def find_rate(lookup_date: date, currency: str, rates_lookup: dict) -> Optional[float]:
    """Find FBIL rate for given date and currency. If no rate, look back up to 7 days."""
    fbil_pair = CURRENCY_MAP.get(currency.upper())
    if not fbil_pair or currency.upper() == "INR":
        return None

    for days_back in range(8):
        check_date = lookup_date - timedelta(days=days_back)
        key = (check_date, fbil_pair)
        if key in rates_lookup:
            return rates_lookup[key]

    return None

def build_rates_lookup(rates_rows: list) -> dict:
    """Build a fast lookup dict from DB rows: (date, currency_pair) -> rate"""
    lookup = {}
    for row in rates_rows:
        key = (row.date, row.currency_pair)
        lookup[key] = row.rate
    return lookup
