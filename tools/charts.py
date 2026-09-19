"""Deterministic chart picker — TOOL. Rule-based."""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def pick_chart(table: pd.DataFrame) -> tuple[str, object]:
    fig, ax = plt.subplots()
    if table.empty or len(table.columns) < 2:
        ax.text(0.5, 0.5, "not enough data", ha="center")
        return "none", fig
    x, y = table.columns[0], table.columns[1]
    try:
        if "date" in x.lower() or "time" in x.lower():
            table.set_index(x)[y].plot(ax=ax, kind="line", marker="o")
            kind = "line"
        elif table[x].nunique() <= 12:
            table.set_index(x)[y].plot(ax=ax, kind="bar")
            kind = "bar"
        else:
            table.set_index(x)[y].head(20).plot(ax=ax, kind="barh")
            kind = "barh"
        ax.set_title(f"{y} by {x}")
        fig.tight_layout()
        return kind, fig
    except Exception:
        ax.text(0.5, 0.5, "chart failed", ha="center")
        return "none", fig
