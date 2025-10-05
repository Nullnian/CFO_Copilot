# agent/metrics.py
from __future__ import annotations
import pandas as pd
import numpy as np

def _split_groups(df: pd.DataFrame):
    rev = df[df["account_category"] == "Revenue"]
    cogs = df[df["account_category"] == "COGS"]
    opex = df[df["account_category"].str.startswith("Opex", na=False)]
    return rev, cogs, opex

def revenue_vs_budget(actuals: pd.DataFrame, budget: pd.DataFrame, month: pd.Period, entity: str | None = None):
    a = actuals[actuals["month"] == month]
    b = budget[budget["month"] == month]
    if entity:
        a = a[a["entity"] == entity]
        b = b[b["entity"] == entity]
    # get Revenue
    a_rev = a[a["account_category"] == "Revenue"]["amount_usd"].sum()
    b_rev = b[b["account_category"] == "Revenue"]["amount_usd"].sum()
    delta = a_rev - b_rev
    pct = (delta / b_rev) * 100 if b_rev != 0 else np.nan
    return {"month": month, "entity": entity or "All", "actual_usd": a_rev, "budget_usd": b_rev, "delta_usd": delta, "delta_pct": pct}

def gross_margin_trend(actuals: pd.DataFrame, last_n: int = 3, entity: str | None = None):
    a = actuals.copy()
    if entity:
        a = a[a["entity"] == entity]
    a = a.groupby(["month", "account_category"], as_index=False)["amount_usd"].sum()
    p = a.pivot_table(index="month", columns="account_category", values="amount_usd", aggfunc="sum").fillna(0.0)
    if "Revenue" not in p.columns: p["Revenue"] = 0.0
    if "COGS" not in p.columns:    p["COGS"]    = 0.0
    p["gross_margin_pct"] = np.where(p["Revenue"]!=0, (p["Revenue"] - p["COGS"]) / p["Revenue"] * 100, np.nan)
    p = p.sort_index().iloc[-last_n:]
    return p.reset_index()

def opex_breakdown(actuals, month=None, entity=None):
    df = actuals.copy()
    if entity:
        df = df[df["entity"] == entity]
    df = df[df["account_category"].str.startswith("Opex")]

    # month
    if month:
        # input
        month = str(month).strip().lower()
        df["month_str"] = df["month"].astype(str).str.lower()

        # match
        matched = df[df["month_str"].str.contains(month)]
        if matched.empty:
            # fallback: use most recent ,onth
            latest = df["month"].dropna().sort_values().iloc[-1]
            print(f"[WARN] No data for '{month}', fallback to latest {latest}")
            month = latest
            matched = df[df["month"] == latest]
        df = matched
    else:
        month = df["month"].dropna().sort_values().iloc[-1]
        df = df[df["month"] == month]

    df = df.groupby("account_category", as_index=False)["amount_usd"].sum()
    total = df["amount_usd"].sum()
    df["pct"] = df["amount_usd"] / total * 100
    return df, total

def ebitda_by_month(actuals: pd.DataFrame, entity: str | None = None):
    a = actuals.copy()
    if entity:
        a = a[a["entity"] == entity]
    rev, cogs, opex = _split_groups(a)
    monthly_rev  = rev.groupby("month")["amount_usd"].sum()
    monthly_cogs = cogs.groupby("month")["amount_usd"].sum()
    monthly_opex = opex.groupby("month")["amount_usd"].sum()
    idx = sorted(set(monthly_rev.index) | set(monthly_cogs.index) | set(monthly_opex.index))
    df = pd.DataFrame(index=idx)
    df["Revenue"] = monthly_rev.reindex(idx).fillna(0.0)
    df["COGS"]    = monthly_cogs.reindex(idx).fillna(0.0)
    df["Opex"]    = monthly_opex.reindex(idx).fillna(0.0)
    df["EBITDA"]  = df["Revenue"] - df["COGS"] - df["Opex"]
    return df.reset_index().rename(columns={"index": "month"})

def cash_runway(cash: pd.DataFrame, actuals: pd.DataFrame, lookback: int = 3, entity: str | None = None):
    c = cash.copy()
    a = actuals.copy()
    if entity:
        c = c[c["entity"] == entity]
        a = a[a["entity"] == entity]

    latest_month = c["month"].max()
    latest_cash_usd = c[c["month"] == latest_month]["cash_balance_usd"].sum()

    e = ebitda_by_month(a, entity=None).set_index("month").sort_index()
    tail = e.iloc[-lookback:]
    
    net_burn = np.maximum(0.0, -tail["EBITDA"])
    avg_burn = net_burn.mean() if len(net_burn) else np.nan

    runway_months = (latest_cash_usd / avg_burn) if (avg_burn and avg_burn > 0) else np.inf
    return {
        "as_of": latest_month,
        "cash_usd": latest_cash_usd,
        "avg_monthly_burn_usd": float(avg_burn) if not np.isnan(avg_burn) else None,
        "runway_months": float(runway_months) if np.isfinite(runway_months) else np.inf
    }
