"""Quick bench: green-r (tuned) + green-r-raw (baseline)."""
import os
from bench_lib import run_bench, summarize

if __name__ == "__main__":
    df = run_bench(tuned="green-r", raw="green-r-raw", limit=4)
    os.makedirs("outputs", exist_ok=True)
    df.to_csv("outputs/bench_green_r.csv", index=False)
    print("\nSummary (green-r / green-r-raw):")
    print(summarize(df, "green-r").to_string())
