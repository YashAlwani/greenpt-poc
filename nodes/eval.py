"""Eval node — scores each method's output, appends rows to results."""

from langgraph.graph import END

from state import BenchmarkState
from tools.eval_tools import check_schema, geval_score

QUALITY_FLOOR = 3   # below this → flag with quality_warning


def eval_node(state: BenchmarkState) -> dict:
    prompt = state["prompt"]
    schema = state["schema"]
    method_results = state.get("method_results", {})
    accumulated = list(state.get("results", []))
    eval_results: dict[str, dict] = {}

    # Baseline tokens_after is the reference for cross-method savings
    baseline = method_results.get("baseline", {})
    baseline_ref = baseline.get("tokens_after", 0) or baseline.get("tokens_before", 0) or 1

    for method, mr in method_results.items():
        decoded = mr.get("decoded_output", {})
        sc = check_schema(decoded, schema)
        g = geval_score(prompt, schema, decoded if decoded else mr.get("raw_output", ""))
        quality_warning = g["score"] < QUALITY_FLOOR

        # Cross-method: how many tokens does this method actually transmit vs baseline?
        this_tokens = mr.get("tokens_after", 0)
        vs_baseline_pct = round((baseline_ref - this_tokens) / baseline_ref * 100, 1) if baseline_ref else 0.0

        eval_results[method] = {
            "score": g["score"],
            "rationale": g["rationale"],
            "schema_valid": sc["valid"],
            "missing_fields": sc["missing_fields"],
            "quality_warning": quality_warning,
        }

        accumulated.append({
            "row_id":            state["row_id"],
            "use_case":          state["use_case"],
            "size":              state["size"],
            "method":            method,
            "tokens_before":     mr["tokens_before"],   # raw model output tokens
            "tokens_after":      mr["tokens_after"],    # what gets transmitted on the wire
            "baseline_tokens":   baseline_ref,          # the reference for vs_baseline_pct
            "token_savings_pct": vs_baseline_pct,       # savings vs baseline (the headline number)
            "self_savings_pct":  mr["token_savings_pct"],  # client-side compression only (for debugging)
            "g_eval_score":      g["score"],
            "g_eval_rationale":  g["rationale"],
            "schema_valid":      sc["valid"],
            "missing_fields":    ",".join(sc["missing_fields"]),
            "status":            mr.get("status", "ok"),
            "quality_warning":   quality_warning,
        })
        flag = " [WARN]" if quality_warning else ""
        print(f"[EVAL]  {method:<19}  vs_baseline={vs_baseline_pct:>5}%  score={g['score']}  schema_valid={sc['valid']}{flag}")

    return {"eval_results": eval_results, "results": accumulated}


def should_continue(state: BenchmarkState):
    """Conditional edge: loop back to simulate if more rows; else END."""
    if state.get("rows_remaining"):
        return "simulate"
    return END
