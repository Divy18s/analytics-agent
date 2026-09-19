"""LLM backend with heuristic fallback (works with no API key)."""
from __future__ import annotations

import json
import os

import agents.prompts as P


def _call(system: str, user: str) -> str | None:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        return None
    try:
        from groq import Groq
        r = Groq(api_key=key).chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1, max_tokens=800)
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return None


def plan(q: str, registry: dict) -> dict | None:
    out = _call(P.PLANNER, f"Q: {q}\nRegistry: {json.dumps(registry)[:2500]}")
    if not out:
        return None
    try:
        return json.loads(out[out.index("{"):out.rindex("}") + 1])
    except Exception:
        return None


def code(plan: dict) -> str | None:
    out = _call(P.CODER, f"Plan: {json.dumps(plan)}")
    return out.replace("```python", "").replace("```", "").strip() if out else None


def narrate(q: str, csv_head: str) -> str | None:
    return _call(P.STORY, f"Q: {q}\nResult:\n{csv_head[:1500]}")
