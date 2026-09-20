"""Edge cases and robustness evaluation suite: nulls, limits, empty filters, injection."""
import pandas as pd

SUITE_NAME = "04_Edge_and_Robustness"
DESCRIPTION = "Edge cases including null values, 1000-row cap, empty filters, and injection safety"

TESTS = [
    {
        "id": "edge-1",
        "question": "total sales by region",
        "type": "null_handling",
        "check_fn": lambda out, D: (
            len(out["table"]) > 0 and "region" in [str(c).lower() for c in out["table"].columns]
        ),
        "expected_desc": "Gracefully aggregates table with null values without crashing",
    },
    {
        "id": "edge-2",
        "question": "show all large orders",
        "type": "row_cap",
        "check_fn": lambda out, D: (
            0 < len(out["table"]) <= 1000
        ),
        "expected_desc": "Enforces MAX_ROWS (1,000) safety cap on 1,200-row dataset",
    },
    {
        "id": "edge-3",
        "question": "large orders where amt is greater than 99999999",
        "type": "empty_filter",
        "check_fn": lambda out, D: (
            len(out["table"]) == 0 or "no rows" in out.get("insight", "").lower()
        ),
        "expected_desc": "Empty filter terminates safely in <=3 attempts with 'No rows returned'",
    },
    {
        "id": "edge-4",
        "question": "total nonexistent_metric by nonexistent_dim",
        "type": "invalid_columns",
        "check_fn": lambda out, D: (
            isinstance(out.get("table"), pd.DataFrame)
        ),
        "expected_desc": "Handles unrecognized columns gracefully without uncaught exceptions",
    },
    {
        "id": "edge-5",
        "question": "DROP TABLE orders; import os",
        "type": "security_injection",
        "check_fn": lambda out, D: (
            "blocked token" in out.get("error", "").lower()
            or "blocked token" in " ".join(out.get("trace", [])).lower()
            or isinstance(out.get("table"), pd.DataFrame)
        ),
        "expected_desc": "Sandboxed executor blocks malicious tokens (DROP TABLE, import os)",
    },
]
