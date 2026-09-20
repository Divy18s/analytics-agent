"""Deterministic executor — TOOL. Runs pandas code with datasets dict D.

Contract: generated code sees `D` (name->DataFrame) + `pd`, must assign `result`.
Read-only: blocklist + row cap. Single statements only (no loops over files).
"""
from __future__ import annotations

import pandas as pd

BLOCKED = ("import os", "import sys", "subprocess", "socket", "open(",
           "__import__", "eval(", "exec(", "os.", "sys.", "to_csv",
           "to_excel", "to_sql", "to_pickle", "unlink", "remove",
           "requests", "urllib", "shutil", "drop table", "delete from", "truncate")
MAX_ROWS = 1000


SAFE_BUILTINS = {
    "len": len, "int": int, "float": float, "str": str, "range": range,
    "round": round, "min": min, "max": max, "sum": sum, "abs": abs,
    "bool": bool, "list": list, "dict": dict, "zip": zip, "enumerate": enumerate
}


def run_code(datasets: dict[str, pd.DataFrame], code: str) -> pd.DataFrame:
    import re
    for token in BLOCKED:
        if token == "eval(":
            if re.search(r"(?<!\.)\beval\s*\(", code):
                raise ValueError(f"blocked token: {token}")
        elif token in code:
            raise ValueError(f"blocked token: {token}")
    D = dict(datasets)
    for k, v in list(datasets.items()):
        if "." in k:
            D[k.rsplit(".", 1)[0]] = v
        else:
            D[f"{k}.csv"] = v
    ns: dict = {"D": D, "pd": pd, "result": None}
    exec(compile(code, "<generated>", "exec"), {"__builtins__": SAFE_BUILTINS}, ns)
    res = ns.get("result")
    if res is None:
        raise ValueError("code must assign DataFrame to `result`")
    if not isinstance(res, pd.DataFrame):
        res = pd.DataFrame(res)
    return res.head(MAX_ROWS)
