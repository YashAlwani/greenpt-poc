"""Tiny side-by-side benchmark runner for GreenPT model variants.

Parameterized by (tuned_model, raw_model) so green-l/-raw and green-r/-raw
can be exercised through identical code. Skips the LangGraph + judge layers
to keep the test fast — measures only what the user asked for: time, tokens,
savings.
"""

import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

import pandas as pd
from openai import OpenAI

from toon import build_key_map, decode, encode
from tools.greentpt_tools import (
    BASELINE_SYSTEM,
    _toon_user_prefix,
    _strip_fences,
    count_tokens,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(_HERE, "generated_llm_dataset.csv")

_client = OpenAI(
    api_key=os.environ.get("GREENPT_API_KEY", ""),
    base_url="https://api.greenpt.ai/v1",
)


def _call(model: str, system: str | None, user: str) -> tuple[str, float]:
    t0 = time.time()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    try:
        resp = _client.chat.completions.create(
            model=model, temperature=0, max_tokens=1024, messages=messages,
        )
        return (resp.choices[0].message.content or "").strip(), time.time() - t0
    except Exception as e:
        return f"__API_ERROR__: {e}", time.time() - t0


def _safe_parse(text: str):
    try:
        return json.loads(_strip_fences(text))
    except Exception:
        return None


def _row_result(method, raw, toon, elapsed):
    tb = count_tokens(raw)
    ta = count_tokens(toon)
    savings = (tb - ta) / tb * 100 if tb > 0 else 0.0
    return {
        "method": method,
        "tokens_before": tb,
        "tokens_after": ta,
        "savings_pct": round(savings, 1),
        "elapsed_s": round(elapsed, 2),
    }


def run_methods(prompt: str, schema: dict, tuned: str, raw: str) -> list[dict]:
    rows = []

    # baseline: raw model, no optimization
    out, t = _call(raw, BASELINE_SYSTEM, prompt)
    parsed = _safe_parse(out)
    toon = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) if parsed else out
    rows.append(_row_result("baseline", out, toon, t))

    # postprocess: raw model, client-side TOON
    out, t = _call(raw, BASELINE_SYSTEM, prompt)
    parsed = _safe_parse(out)
    if parsed:
        km = build_key_map(parsed)
        toon = encode(parsed, km)
    else:
        toon = out
    rows.append(_row_result("postprocess", out, toon, t))

    # prompt_engineering: tuned model
    out, t = _call(tuned, None, prompt)
    parsed = _safe_parse(out)
    toon = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) if parsed else out
    rows.append(_row_result("prompt_engineering", out, toon, t))

    # combined: tuned model + TOON instructions in user msg
    km = build_key_map(schema)
    user = _toon_user_prefix(km) + prompt
    out, t = _call(tuned, None, user)
    parsed = _safe_parse(out)
    if parsed:
        try:
            decoded = decode(json.dumps(parsed), km)
            toon = encode(decoded, km)
        except Exception:
            toon = out
    else:
        toon = out
    rows.append(_row_result("combined", out, toon, t))

    return rows


def run_bench(tuned: str, raw: str, limit: int = 4) -> pd.DataFrame:
    df = pd.read_csv(DATASET)
    # one row per use_case for breadth
    sampled = df.groupby("use_case").head(1).head(limit)
    all_rows = []
    print(f"\n>>> Bench: tuned={tuned}  raw={raw}  rows={len(sampled)}")
    for _, r in sampled.iterrows():
        schema = json.loads(r["expected_output_schema"]) if isinstance(r["expected_output_schema"], str) else {}
        print(f"  [{r['id']}] {r['use_case']}")
        results = run_methods(r["prompt"], schema, tuned, raw)
        for res in results:
            res["row_id"] = r["id"]
            res["use_case"] = r["use_case"]
            all_rows.append(res)
            print(f"    {res['method']:20s} tokens {res['tokens_before']:4d}->{res['tokens_after']:4d}"
                  f"  savings {res['savings_pct']:5.1f}%  time {res['elapsed_s']:5.2f}s")
    return pd.DataFrame(all_rows)


def summarize(df: pd.DataFrame, label: str) -> pd.DataFrame:
    agg = df.groupby("method").agg(
        mean_tokens_before=("tokens_before", "mean"),
        mean_tokens_after=("tokens_after", "mean"),
        mean_savings_pct=("savings_pct", "mean"),
        mean_time_s=("elapsed_s", "mean"),
        total_time_s=("elapsed_s", "sum"),
    ).round(2)
    agg["model_variant"] = label
    return agg
