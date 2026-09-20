"""LLM backend with heuristic fallback (works with no API key)."""
from __future__ import annotations

import json
import os

from dotenv import load_dotenv

import agents.prompts as P

load_dotenv()


MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]


def _call(system: str, user: str) -> str | None:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        return None
    preferred = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    models_to_try = [preferred] + [m for m in MODELS if m != preferred]

    try:
        from groq import Groq
        client = Groq(api_key=key)
        for model in models_to_try:
            try:
                r = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.1, max_tokens=800)
                content = (r.choices[0].message.content or "").strip()
                if content:
                    return content
            except Exception as e:
                print(f"[LLM error with model '{model}': {e}]")
        return None
    except Exception as e:
        print(f"[Groq client error: {e}]")
        return None


def plan(q: str, registry: dict) -> dict | None:
    out = _call(P.PLANNER, f"Q: {q}\nRegistry: {json.dumps(registry)[:16000]}")
    if not out:
        return None
    try:
        return json.loads(out[out.index("{"):out.rindex("}") + 1])
    except Exception:
        return None


def code(plan: dict, question: str = "") -> str | None:
    prompt = f"Question: {question}\nPlan: {json.dumps(plan)}" if question else f"Plan: {json.dumps(plan)}"
    out = _call(P.CODER, prompt)
    return out.replace("```python", "").replace("```", "").strip() if out else None


def fix_code(plan: dict, code_str: str, err: str, question: str = "") -> str | None:
    prompt = (
        f"Question: {question}\n"
        f"Plan: {json.dumps(plan)}\n"
        f"Broken Code:\n{code_str}\n"
        f"Execution Error:\n{err}\n"
        "Fix the code and output ONLY valid pandas code assigned to `result`."
    )
    out = _call(P.CODER, prompt)
    return out.replace("```python", "").replace("```", "").strip() if out else None


def narrate(q: str, csv_head: str) -> str | None:
    if not csv_head or not csv_head.strip():
        return None
    return _call(P.STORY, f"Q: {q}\nResult:\n{csv_head[:3000]}")

