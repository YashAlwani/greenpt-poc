"""GreenPT main node — runs all 4 methods for the current row and records results."""

from state import BenchmarkState
from tools.greentpt_tools import METHODS


def greentpt_node(state: BenchmarkState) -> dict:
    """Run baseline, postprocess, prompt_engineering, combined for the current row."""
    prompt = state["prompt"]
    schema = state["schema"]
    method_results: dict[str, dict] = {}

    for name, runner in METHODS.items():
        result = runner(prompt, schema)
        method_results[name] = result
        status = result.get("status", "ok")
        print(
            f"[GPT]   {name:<19}  "
            f"tokens {result['tokens_before']:>4}->{result['tokens_after']:<4}  "
            f"savings {result['token_savings_pct']:>5}%  "
            f"[{status}]"
        )

    return {"method_results": method_results}
