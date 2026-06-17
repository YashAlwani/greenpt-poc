"""Eval agent tools.

check_schema: structural validation (cheap, no LLM).
geval_score:  1–5 quality score from a cheap LLM judge.
"""

import json
import os
import re

from openai import OpenAI

GREENPT_BASE = "https://api.greenpt.ai/v1"
JUDGE_MODEL = "mistral-small-3.2-24b-instruct-2506"  # €0.15/€0.35 per 1M

_client = OpenAI(
    api_key=os.environ.get("GREENPT_API_KEY", ""),
    base_url=GREENPT_BASE,
)

GEVAL_SYSTEM = """You are an expert evaluator for structured data extraction quality.
Score the output on a 1–5 scale:

5 — All required fields present and correct. Types match schema. No hallucination.
4 — Nearly all fields correct; one minor error or a missing optional field.
3 — Core fields present but notable errors (wrong value, wrong type, missing required field).
2 — Partial extraction. Multiple fields missing or wrong.
1 — Output is malformed, missing, empty, or completely incorrect.

Respond with JSON only — no prose, no markdown:
{"score": <1-5>, "rationale": "<one sentence>"}"""


def check_schema(output, schema: dict) -> dict:
    """Cheap structural check — does the output dict have the required keys?

    Returns {valid: bool, missing_fields: list[str]}.
    No LLM call.
    """
    if not isinstance(output, dict):
        return {"valid": False, "missing_fields": list(schema.keys())}
    required = set(schema.keys())
    present = set(output.keys())
    missing = sorted(required - present)
    return {"valid": len(missing) == 0, "missing_fields": missing}


def _build_judge_prompt(original_prompt: str, expected_schema: dict, actual_output) -> str:
    snippet = (original_prompt or "")[:600]
    if isinstance(actual_output, dict):
        actual_str = json.dumps(actual_output, indent=2)[:1500]
    else:
        actual_str = str(actual_output or "")[:1500]
    return (
        f"## Extraction task (first 600 chars)\n{snippet}\n\n"
        f"## Expected output schema\n{json.dumps(expected_schema, indent=2)}\n\n"
        f"## Actual output to evaluate\n{actual_str}"
    )


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        t = "\n".join(lines).strip()
    return t


def _parse_judge(text: str) -> dict:
    t = _strip_fences(text)
    try:
        parsed = json.loads(t)
        score = int(parsed.get("score", 1))
        return {
            "score": max(1, min(5, score)),
            "rationale": str(parsed.get("rationale", ""))[:300],
        }
    except Exception:
        m = re.search(r'"?score"?\s*:\s*([1-5])', t)
        return {"score": int(m.group(1)) if m else 1, "rationale": "parse error"}


def geval_score(original_prompt: str, expected_schema: dict, actual_output) -> dict:
    """G-Eval: returns {score: 1-5, rationale: str}."""
    try:
        resp = _client.chat.completions.create(
            model=JUDGE_MODEL,
            temperature=0,
            max_tokens=256,
            messages=[
                {"role": "system", "content": GEVAL_SYSTEM},
                {"role": "user", "content": _build_judge_prompt(original_prompt, expected_schema, actual_output)},
            ],
        )
        return _parse_judge(resp.choices[0].message.content or "")
    except Exception as e:
        return {"score": 1, "rationale": f"judge call failed: {e}"}
