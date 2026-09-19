"""Generates 3 small CSVs proving generality + join: orders <-> customers on cid."""
import pandas as pd
from pathlib import Path

out = Path(__file__).resolve().parent.parent / "data"
out.mkdir(exist_ok=True)
customers = pd.DataFrame({"cid": [1, 2, 3, 4], "city": ["HYD", "DEL", "HYD", "BLR"], "tier": ["gold", "silver", "gold", "silver"]})
orders = pd.DataFrame({"oid": range(1, 9), "cid": [1, 2, 1, 3, 4, 2, 3, 1], "amt": [500, 200, 700, 300, 900, 150, 400, 600]})
hr = pd.DataFrame({"emp": ["a", "b", "c", "d", "e"], "dept": ["eng", "ops", "eng", "ops", "eng"], "salary": [90, 60, 95, 55, 100]})
customers.to_csv(out / "customers.csv", index=False)
orders.to_csv(out / "orders.csv", index=False)
hr.to_csv(out / "hr.csv", index=False)
print("wrote", [str(p) for p in out.glob('*.csv')])
