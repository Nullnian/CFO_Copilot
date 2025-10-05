import pandas as pd
from pathlib import Path

def prepare_csv_from_excel(xlsx_path="data.xlsx", outdir="fixtures"):
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)

    actuals = pd.read_excel(xlsx_path, sheet_name="actuals")
    budget = pd.read_excel(xlsx_path, sheet_name="budget")
    cash = pd.read_excel(xlsx_path, sheet_name="cash")
    fx = pd.read_excel(xlsx_path, sheet_name="fx")

    actuals.to_csv(outdir / "actuals.csv", index=False)
    budget.to_csv(outdir / "budget.csv", index=False)
    cash.to_csv(outdir / "cash.csv", index=False)
    fx.to_csv(outdir / "fx.csv", index=False)

    print(f"path: {outdir}/")

if __name__ == "__main__":
    prepare_csv_from_excel("data.xlsx", "fixtures")