"""GreenPT agent tools.

The 4 optimization method tools + TOON helpers + token counter. All LLM calls
go through GreenPT's OpenAI-compatible endpoint.

Ruleset enforced here:
- temperature=0, max_tokens=1024 across all methods (fairness)
- baseline uses green-l-raw (no system prompt)
- optimized methods use green-l (GreenPT's tuned system prompt)
- deterministic key_map for combined: model is told the exact abbreviations
- failure modes: parse_failed, decode_failed, api_failed (logged, not raised)
"""

import json
import os

import tiktoken
from openai import OpenAI

from toon import build_key_map, decode, encode

GREENPT_BASE = "https://api.greenpt.ai/v1"
TEMPERATURE = 0
MAX_TOKENS = 1024

_client = OpenAI(
    api_key=os.environ.get("GREENPT_API_KEY", ""),
    base_url=GREENPT_BASE,
)
_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Token count via tiktoken cl100k_base (OpenAI-compatible)."""
    return len(_enc.encode(text or ""))


BASELINE_SYSTEM = (
    "You are a structured data extraction API. "
    "Return ONLY valid JSON matching the schema provided. "
    "No explanation. No markdown. No code fences."
)


def _toon_user_prefix(key_map: dict) -> str:
    """Prepended to the user message for `combined` — green-l rejects system prompts,
    so the TOON instructions ride in the user message.
    """
    km_json = json.dumps(key_map, separators=(",", ":"))
    return (
        "OUTPUT INSTRUCTIONS — apply to your JSON answer below:\n"
        f"1. Rename keys using this exact map: {km_json} (keys not in the map stay as-is).\n"
        "2. Output minified JSON — no whitespace, no newlines.\n"
        "3. Never include the map in your output. No markdown. No code fences.\n\n"
        "TASK:\n"
    )


def _call(model: str, system: str | None, user: str) -> str:
    """One LLM call. Returns the raw text content or __API_ERROR__: ... on failure.

    `green-l` and `green-r` (non-raw GreenPT models) reject system prompts —
    they ship with GreenPT's built-in optimization prompt. Pass system=None
    for those models.
    """
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        resp = _client.chat.completions.create(
            model=model,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            messages=messages,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return f"__API_ERROR__: {e}"


def _strip_fences(text: str) -> str:
    """Strip ```json … ``` fences if the model added them anyway."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        t = "\n".join(lines).strip()
    return t


def _safe_parse(text: str):
    """Parse JSON, return None on failure."""
    try:
        return json.loads(_strip_fences(text))
    except (json.JSONDecodeError, ValueError):
        return None


def _result(method: str, raw: str, toon: str, key_map: dict, decoded, status: str = "ok") -> dict:
    tb = count_tokens(raw)
    ta = count_tokens(toon)
    savings = (tb - ta) / tb * 100 if tb > 0 else 0.0
    return {
        "method": method,
        "raw_output": raw,
        "toon_output": toon,
        "key_map": key_map,
        "decoded_output": decoded if isinstance(decoded, dict) else {},
        "tokens_before": tb,
        "tokens_after": ta,
        "token_savings_pct": round(savings, 1),
        "status": status,
    }


# ── 4 method tools ────────────────────────────────────────────────────────────

def call_baseline(prompt: str, schema: dict) -> dict:
    """green-l-raw + vanilla extraction prompt. No optimization. Reference point."""
    raw = _call("green-l-raw", BASELINE_SYSTEM, prompt)
    if raw.startswith("__API_ERROR__"):
        return _result("baseline", raw, raw, {}, None, status="api_failed")
    parsed = _safe_parse(raw)
    # baseline "toon_output" is just the minified version of what the model returned
    toon = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) if parsed else raw
    if parsed is None:
        return _result("baseline", raw, toon, {}, None, status="parse_failed")
    return _result("baseline", raw, toon, {}, parsed)


def call_postprocess(prompt: str, schema: dict) -> dict:
    """green-l-raw + vanilla prompt, then client-side TOON-encode the output."""
    raw = _call("green-l-raw", BASELINE_SYSTEM, prompt)
    if raw.startswith("__API_ERROR__"):
        return _result("postprocess", raw, raw, {}, None, status="api_failed")
    parsed = _safe_parse(raw)
    if parsed is None:
        return _result("postprocess", raw, raw, {}, None, status="parse_failed")
    key_map = build_key_map(parsed)
    toon = encode(parsed, key_map)
    try:
        decoded = decode(toon, key_map)
    except Exception:
        return _result("postprocess", raw, toon, key_map, parsed, status="decode_failed")
    return _result("postprocess", raw, toon, key_map, decoded)


def call_prompt_engineering(prompt: str, schema: dict) -> dict:
    """green-l with NO system prompt — its built-in GreenPT optimization is the system prompt."""
    raw = _call("green-l", None, prompt)
    if raw.startswith("__API_ERROR__"):
        return _result("prompt_engineering", raw, raw, {}, None, status="api_failed")
    parsed = _safe_parse(raw)
    if parsed is None:
        return _result("prompt_engineering", raw, raw, {}, None, status="parse_failed")
    toon = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    return _result("prompt_engineering", raw, toon, {}, parsed)


def call_combined(prompt: str, schema: dict) -> dict:
    """green-l + deterministic TOON. green-l rejects system prompts, so the
    TOON instructions ride in the user message.
    """
    key_map = build_key_map(schema)
    user = _toon_user_prefix(key_map) + prompt
    raw = _call("green-l", None, user)
    if raw.startswith("__API_ERROR__"):
        return _result("combined", raw, raw, key_map, None, status="api_failed")
    parsed = _safe_parse(raw)
    if parsed is None:
        return _result("combined", raw, raw, key_map, None, status="parse_failed")
    try:
        # If the model used our short keys, decode restores them via inverted map;
        # if it used long keys, decode is a no-op.
        decoded = decode(json.dumps(parsed), key_map)
        toon = encode(decoded, key_map)
    except Exception:
        return _result("combined", raw, raw, key_map, parsed, status="decode_failed")
    return _result("combined", raw, toon, key_map, decoded)


METHODS = {
    "baseline":           call_baseline,
    "postprocess":        call_postprocess,
    "prompt_engineering": call_prompt_engineering,
    "combined":           call_combined,
}
