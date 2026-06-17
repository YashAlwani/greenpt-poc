# GreenPT — Benchmark Pipeline POC

## Product context

GreenPT is an API that optimises LLM usage for sustainability by reducing token consumption while preserving output quality.

- The product hosts its own model (Mistral Small 3.2 24B) on green data centres.
- Model routing between external providers is **not** in scope. Optimization happens at the **output / prompt level**, not by switching models.
- Two pricing tiers exist for the product (not part of this POC):
  - **GreenL** — €0.25/M input, €0.80/M output. Aggressive optimization, tight `max_tokens`, full JSON/TOON processing.
  - **GreenR** — €0.35/M input, €0.95/M output. Conservative optimization, quality-first.

## What this POC is

The POC is the **benchmarking / evaluation pipeline** for the JSON optimization tool. It is the measurement layer that tells us whether our optimization methods actually save tokens without destroying quality.

The pipeline compares **3 optimization methods** (plus a baseline) across **4 use cases** × **3 prompt sizes**, scores each output for quality with G-Eval, and produces a results table.

## Optimization methods being compared

1. **Post-processing** — run a normal LLM call, then compress the output with code afterwards.
2. **Prompt engineering** — rewrite the system prompt so the model produces lean JSON natively.
3. **Combined** — both methods stacked.

A baseline (no optimization) is needed as the reference point for token savings %.

## Use cases

1. **invoice_parsing** — structured data extraction, flat JSON.
2. **resume_parsing** — structured data extraction, moderate nesting.
3. **intent_classification** — text analysis & classification.
4. **summarization** — content generation with metadata, deeper nesting.

## Prompt sizes (input tokens)

- **S**: ~300–500
- **M**: ~500–700
- **L**: ~800–1000

## Dataset shape

- 4 use cases × 3 sizes × 4 rows = **48 rows total**.
- Each row is run through all 4 methods (baseline + 3) → **192 scored outputs**.

### Key separation principle

- **Schemas are hardcoded** in the generation script.
- The LLM only generates the **source text** for each row.
- This keeps reference outputs stable across runs.

### Do not confuse

- **Generation prompts** — used once to build the dataset.
- **G-Eval judging prompts** — used at evaluation time, and only receive `reference_output` + `actual_output`. They do not see the original generation instructions.

## Scoring

- **G-Eval** (LLM-as-judge) produces a **1–5 quality score** per output, on dimensions like faithfulness and correctness.
- Token savings % is always computed as:
  `(tokens_before − tokens_after) / tokens_before × 100`, reported to **one decimal place**.

### Results table — required columns

| use_case | size | method | token_savings_% | g_eval_score |

(Additional columns like `row_id`, raw token counts, and judge rationale are fine to include for debugging, but the five above are the contract.)

## Domain definitions

- **TOON format** — a JSON compression technique that reduces token usage 30–60% by shortening key names, removing whitespace, and restructuring nesting. Core GreenPT output optimization method.
- **G-Eval** — LLM-as-judge framework that scores output quality on defined dimensions on a 1–5 scale.
- **Prompt caching** — caching the transformer's key/value computation of repeated input prefixes. **Not** caching outputs or semantic responses. Keep this distinction strict.
- **Token savings %** — see formula above.

## File / output conventions

- Generated artifacts go to `/mnt/user-data/outputs/`.
- Scripts must be runnable with standard `pip install` + an `ANTHROPIC_API_KEY` env variable.
- CSV datasets must include spot-check notes validating structure.
- Read the relevant `SKILL.md` before producing any `.docx`, `.pdf`, `.pptx`, or `.xlsx`.

## Relevant Jira tickets (SCRUM project)

| Ticket    | Topic |
|-----------|-------|
| SCRUM-11  | Quality benchmarks (G-Eval, human rubric) |
| SCRUM-13  | JSON optimization (TOON, minification, structured output) |
| SCRUM-16  | Agent vs. freeform routing |
| SCRUM-21  | Use case categories + S/M/L size definitions |
| SCRUM-22  | Benchmark runner script |
| SCRUM-25  | G-Eval automated scoring |
| SCRUM-26  | Human / non-technical evaluation rubric |
| SCRUM-27  | Sized prompt dataset (S/M/L) |
| SCRUM-28  | Usable context for tool spec |

Atlassian identifiers:
- Cloud ID: `da5618ea-f909-4c90-a233-eff6e84b1853`
- Project key: `SCRUM`
- Confluence space ID: `1343492`

## Team

- **Yash** (owner of this POC)
- Finn
- Jordy

## Working style for Claude Code

- Act on confirmed decisions. Don't re-ask.
- One clarifying question at a time, only if blocking.
- Dense and direct over thorough and padded.
- Flag assumptions inline in one line rather than stopping.
- Prose for explanations; tables for comparisons.

## Out of scope for this POC

- Real-time GreenPT API endpoint and the GreenL/GreenR pricing tiers.
- Multi-model routing.
- Caching infrastructure.
- Production deployment.

(Note: a Flask developer console — `app.py` — now ships with the POC as a demo surface. It is not a production UI.)
