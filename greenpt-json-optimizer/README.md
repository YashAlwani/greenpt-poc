# greenpt-poc

Benchmark POC for GreenPT — measures token savings of TOON compression and prompt-engineering optimization on top of GreenPT's hosted models, without sacrificing output quality.

## What this is

A 3-agent LangGraph pipeline that:

1. **Simulation Agent** — replays rows from a 48-row test dataset (4 use cases × 3 sizes × 4 rows)
2. **GreenPT Agent** — runs 4 optimization methods against each row and measures tokens
3. **Eval Agent** — scores each output 1–5 using G-Eval (LLM-as-judge)

Output: a results CSV with `use_case | size | method | token_savings_% | g_eval_score`.

## Methods benchmarked

| Method | Model | Optimization layer |
|---|---|---|
| `baseline` | `green-l-raw` | none — reference point |
| `postprocess` | `green-l-raw` + local TOON encoder | client-side compression after generation |
| `prompt_engineering` | `green-l` | GreenPT's built-in tuned system prompt |
| `combined` | `green-l` + local TOON encoder | both layers stacked |

Same underlying model (Mistral Small 3.2 24B) for all four — only the optimization layer changes.

## Quick start

```bash
pip install -r requirements.txt
echo "GREENPT_API_KEY=sk-..." > .env
python run.py --limit 2          # process 2 rows × 4 methods
python run.py                    # full 48-row benchmark
```

Results land in `outputs/results.csv`.

## Files

- `toon.py` — TOON compression engine
- `state.py` — LangGraph state shape
- `graph.py` — graph wiring
- `nodes/` — the 3 agent node functions
- `tools/` — LangChain `@tool` wrappers
- `run.py` — CLI entry point
- `generated_llm_dataset.csv` — 48-row evaluation dataset (invoice_parsing, resume_parsing, summarization, intent_classification × S/M/L)
- `PROJECT.md` — full product/POC spec
