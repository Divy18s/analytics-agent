"""Deterministic multi-dataset profiler — TOOL, not an agent (no LLM)."""
from __future__ import annotations

import pandas as pd


def _time_cols(df: pd.DataFrame) -> list[str]:
    out = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            out.append(col)
        elif df[col].dtype == object and len(df):
            try:
                if pd.to_datetime(df[col].dropna().head(50), errors="coerce").notna().mean() > 0.8:
                    out.append(col)
            except Exception:
                pass
    return out


def profile_one(name: str, df: pd.DataFrame) -> dict:
    cols = [{
        "name": c,
        "dtype": str(df[c].dtype),
        "null_pct": round(float(df[c].isna().mean() * 100), 2),
        "n_unique": int(df[c].nunique(dropna=True)),
        "sample": [str(x) for x in df[c].dropna().head(3).tolist()],
    } for c in df.columns]
    return {"name": name, "rows": int(len(df)), "columns": cols,
            "numeric": df.select_dtypes(include="number").columns.tolist(),
            "cats": [c for c in df.columns if c not in df.select_dtypes(include="number").columns][:50],
            "time": _time_cols(df)}


def profile_all(datasets: dict[str, pd.DataFrame]) -> dict:
    profs = {n: profile_one(n, df) for n, df in datasets.items()}
    # join candidates: shared column names across files
    names = list(datasets)
    shared: dict[str, list[str]] = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            common = [c for c in datasets[names[i]].columns if c in datasets[names[j]].columns]
            if common:
                shared[f"{names[i]}<->{names[j]}"] = common
    return {"datasets": profs, "join_candidates": shared}
