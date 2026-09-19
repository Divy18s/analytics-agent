"""Deterministic executor — TOOL. Runs pandas code with datasets dict D.

Contract: generated code sees `D` (name->DataFrame) + `pd`, must assign `result`.
Read-only: blocklist + row cap. Single statements only (no loops over files).
"""
from __future__ import annotations

import pandas as pd

BLOCKED = ("import os", "import sys", "subprocess", "socket", "open(",
           "__import__", "eval(", "exec(", "os.", "sys.", "to_csv",
           "to_excel", "to_sql", "to_pickle", "unlink", "remove",
           "requests", "urllib", "shutil")
MAX_ROWS = 1000


def run_code(datasets: dict[str, pd.DataFrame], code: str) -> pd.DataFrame:
    for token in BLOCKED:
        if token in code:
            raise ValueError(f"blocked token: {token}")
    ns: dict = {"D": dict(datasets), "pd": pd, "result": None}
    exec(compile(code, "<generated>", "exec"), {"__builtins__": {}}, ns)
    res = ns.get("result")
    if res is None:
        raise ValueError("code must assign DataFrame to `result`")
    if not isinstance(res, pd.DataFrame):
        res = pd.DataFrame(res)
    return res.head(MAX_ROWS)
