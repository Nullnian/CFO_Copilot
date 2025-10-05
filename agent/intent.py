# agent/intent.py
from __future__ import annotations
import re
from dateutil import parser
import pandas as pd
import re
import calendar
from datetime import datetime

MONTH_RE = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}"

def parse_month_from_text(text: str):
    """Parse month like 'June 2025', '2025 July', 'Jan-23', 'Jul 25'."""
    text = text.strip().lower()
    match = re.search(r"([A-Za-z]+)\s*(\d{2,4})", text)
    if not match:
        return None
    month_name, year = match.groups()
    month_name = month_name.capitalize()

    # month str -> int
    try:
        month_num = list(calendar.month_abbr).index(month_name[:3])
    except ValueError:
        return None

    # year
    year = int(year)
    if year < 100:
        year += 2000

    return f"{year}-{month_num:02d}"

def parse_last_n(text: str, default=3):
    """
    Detect phrases like 'last 3 months', 'past 5 month', '3 month on', 'show 5 months', etc.
    """
    text = text.lower()
    match = re.search(r"(\d+)\s*(month|months|mon|mo|monthon|monthes)?", text)
    if match:
        try:
            return int(match.group(1))
        except:
            pass
    return default

def classify_intent(q: str):
    ql = q.lower()
    if "runway" in ql or ("cash" in ql and "runway" in ql):
        return "cash_runway"
    if "gross" in ql and "margin" in ql:
        return "gross_margin_trend"
    if "opex" in ql and ("breakdown" in ql or "by category" in ql or "split" in ql):
        return "opex_breakdown"
    if "ebitda" in ql:
        return "ebitda_trend"
    if "revenue" in ql and "budget" in ql:
        return "revenue_vs_budget"
    if "revenue" in ql:
        return "revenue_vs_budget"
    return "unknown"
