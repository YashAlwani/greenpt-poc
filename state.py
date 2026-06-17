"""LangGraph state shape for the GreenPT benchmark pipeline."""

from typing import TypedDict


class BenchmarkState(TypedDict, total=False):
    # Dataset control
    rows_remaining: list[dict]   # rows not yet processed
    results: list[dict]          # flat accumulated results (one row per row × method)

    # Current row (set by simulate_node)
    row_id: str
    use_case: str
    size: str
    prompt: str
    schema: dict

    # GreenPT outputs (set by greentpt_node) — keyed by method name
    # {method: {raw_output, toon_output, key_map, decoded_output,
    #           tokens_before, tokens_after, token_savings_pct, status}}
    method_results: dict

    # Eval outputs (set by eval_node) — keyed by method name
    # {method: {score, rationale, schema_valid, missing_fields}}
    eval_results: dict
