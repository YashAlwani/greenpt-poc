"""Quick bench: green-l (tuned) + green-l-raw (baseline)."""
import os
from bench_lib import run_bench, summarize

if __name__ == "__main__":
    df = run_bench(tuned="green-l", raw="green-l-raw", limit=4)
    os.makedirs("outputs", exist_ok=True)
    df.to_csv("outputs/bench_green_l.csv", index=False)
    print("\nSummary (green-l / green-l-raw):")
    print(summarize(df, "green-l").to_string())
