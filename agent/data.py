from __future__ import annotations
import pandas as pd
from dateutil import parser
from pathlib import Path


def _parse_month(s: str):
    if isinstance(s, pd.Period):
        return s
    dt = parser.parse(str(s))
    return pd.Period(dt.strftime("%Y-%m"), freq="M")


def load_data(fixtures_dir: str | Path):
    fixtures_dir = Path(fixtures_dir)

    actuals = pd.read_csv(fixtures_dir / "actuals.csv")
    budget = pd.read_csv(fixtures_dir / "budget.csv")
    cash = pd.read_csv(fixtures_dir / "cash.csv")
    fx = pd.read_csv(fixtures_dir / "fx.csv")


    for df in (actuals, budget):
        if "account_category" not in df.columns:
            for cand in ["account_c", "account", "accountCategory"]:
                if cand in df.columns:
                    df.rename(columns={cand: "account_category"}, inplace=True)
                    break

    for df in [actuals, budget, cash]:
        if "month" in df.columns:
            # clean data 
            df["month"] = df["month"].astype(str).str.strip()
            df = df[df["month"].str.lower() != "nan"]  

            def safe_parse(m):
                try:
                    return pd.to_datetime(m, format="%b-%y")
                except Exception:
                    try:
                        return pd.to_datetime(m, format="%Y-%m")
                    except Exception:
                        try:
                            return pd.to_datetime(m, format="%b %Y")
                        except Exception:
                            return pd.NaT

            df["month"] = df["month"].apply(safe_parse)
            df["month"] = df["month"].dt.strftime("%Y-%m")

    fx = fx.rename(columns={"rate_to_usd": "rate_to_usd"})
    if "rate_to_usd" not in fx.columns:
        for cand in ["usd_rate", "to_usd", "rate"]:
            if cand in fx.columns:
                fx.rename(columns={cand: "rate_to_usd"}, inplace=True)
                break
    fx_key = ["month", "currency"]
    if fx.duplicated(fx_key).any():
        fx = fx.drop_duplicates(fx_key, keep="last")

    def to_usd(df, amount_col):
        if "currency" not in df.columns:
            df[amount_col + "_usd"] = df[amount_col].astype(float)
            return df
        df = df.merge(fx, on=["month", "currency"], how="left", validate="m:1")
        df["rate_to_usd"] = df["rate_to_usd"].fillna(1.0)
        df[amount_col + "_usd"] = df[amount_col].astype(float) * df["rate_to_usd"].astype(float)
        return df

    # transfer actuals & budget 
    actuals = to_usd(actuals, "amount")
    budget = to_usd(budget, "amount")

    #  process cash
    if "cash_usd" in cash.columns:
        cash = cash.rename(columns={"cash_usd": "cash_balance_usd"})
    elif "cash_balance" in cash.columns:
        # have cash_balance but no currency -> USD
        cash["currency"] = "USD"
        cash = to_usd(cash, "cash_balance")
    else:
        raise ValueError("cash file must include 'cash_usd' or 'cash_balance' column")

    return actuals, budget, cash
