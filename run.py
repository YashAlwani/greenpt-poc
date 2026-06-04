"""
GreenPT benchmark CLI.

Usage:
    python run.py                  # full 36-row x 4-method run
    python run.py --limit 2        # 2 rows only — quick smoke test
    python run.py --limit 1        # 1 row — fastest end-to-end check
"""

import argparse
import json
import os
import sys
import time

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_BASE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(_BASE, "generated_llm_dataset.csv")
OUTPUT_DIR = os.path.join(_BASE, "outputs")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "results.csv")


def load_rows(limit: int | None) -> list[dict]:
    df = pd.read_csv(DATASET)
    if limit:
        df = df.head(limit)
    return df.to_dict("records")


def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 76)
    print("RESULTS SUMMARY")
    print("=" * 76)
    by_method = (
        df.groupby("method")
        .agg(
            mean_savings=("token_savings_pct", "mean"),
            mean_score=("g_eval_score", "mean"),
            rows=("row_id", "count"),
        )
        .round(2)
    )
    print(by_method.to_string())
    print()
    if "use_case" in df.columns:
        print("Mean token_savings_% by use_case x method:")
        pivot = df.pivot_table(
            index="use_case",
            columns="method",
            values="token_savings_pct",
            aggfunc="mean",
        ).round(1)
        print(pivot.to_string())
        print()
        print("Mean g_eval_score by use_case x method:")
        pivot2 = df.pivot_table(
            index="use_case",
            columns="method",
            values="g_eval_score",
            aggfunc="mean",
        ).round(2)
        print(pivot2.to_string())
    print("=" * 76)


def main() -> int:
    parser = argparse.ArgumentParser(description="GreenPT benchmark runner")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to process")
    args = parser.parse_args()

    if not os.environ.get("GREENPT_API_KEY"):
        print("ERROR: GREENPT_API_KEY not set. Copy .env.example to .env and fill it in.")
        return 1

    # Import after env is loaded
    from graph import build_graph

    rows = load_rows(args.limit)
    total = len(rows)
    print(f"Loaded {total} rows x 4 methods = {total * 4} GreenPT calls + {total * 4} judge calls")
    print(f"Output -> {OUTPUT_CSV}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    graph = build_graph()

    initial = {"rows_remaining": rows, "results": []}
    t0 = time.time()
    # Bump recursion limit so the loop can process all rows
    final = graph.invoke(initial, config={"recursion_limit": total * 10 + 50})
    elapsed = time.time() - t0
    print(f"\nFinished {total} rows in {elapsed:.1f}s")

    results = final.get("results", [])
    if not results:
        print("No results produced.")
        return 1

    out_df = pd.DataFrame(results)
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {len(out_df)} result rows to {OUTPUT_CSV}")

    print_summary(out_df)

    # Sanity checks
    baseline_rows = out_df[out_df["method"] == "baseline"]
    bad_baseline = baseline_rows[baseline_rows["token_savings_pct"] != 0.0]
    if not bad_baseline.empty:
        print(f"NOTE: {len(bad_baseline)} baseline rows show non-zero savings — "
              f"this is OK if the model added whitespace that we minified.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
