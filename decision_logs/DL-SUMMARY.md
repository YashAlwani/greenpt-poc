# GreenPT POC — Decision Log Summary

The story of benchmarking a JSON optimization API, one decision at a time.

**Thread:** Rules → Dataset → Pipeline → Math → Findings → SDK → Demo → Report

---

## DL-01 — Lock the rules before any data touches them
`1 [DL] How do we lock benchmark rules before any data runs so results stay defensible.txt`

Started with a pitch: "GreenPT cuts tokens without cutting quality." But that claim needs a number, and a number needs a methodology. Without pinning compute, temperature, failure handling, and savings math upfront, any savings percentage a reviewer could poke holes through. Eight rules written as source-code constants before the pipeline ran a single row. Not a README. Constants in the tools module that every method call reads.

**Decision:** Eight fairness rules encoded in `tools/greentpt_tools.py` — TEMPERATURE = 0, MAX_TOKENS = 1024, typed failure statuses, cross-method savings denominator.
**GAP → DL-02:** Rules exist. Nothing to run them against.

---

## DL-02 — Build rows the optimizer actually has to work for
`2 [DL] How should I design a benchmark dataset that won't contaminate savings measurements.txt`

The temptation was to generate a bunch of prompts and run them through the methods. That's wrong — prompts aren't the variable the optimizer acts on, schemas are. A 300-token invoice asking for 2 fields and a 300-token invoice asking for 12 nested line-item objects are completely different benchmarks. Locked four use cases: one savings stress test, one nested-schema test, one quality trade-off test, one no-op control. Schemas hardcoded. Source text agent-generated. 48 rows, $0.32.

**Decision:** Hybrid generation — hardcoded schemas (reproducible ground truth) + Claude-generated source text (content variety). 4 use cases × 3 sizes × 4 rows = 48 prompts.
**GAP → DL-03:** Dataset exists. Need a pipeline to run it through all four methods.

---

## DL-03 — Build a pipeline the methodology diagram can sell
`3 [DL] Should I use LangGraph or a simple loop for the benchmark pipeline.txt`

A plain for-loop would produce the same CSV. But the CSV is not the deliverable — the methodology story is. When a client asks "how do you know the savings number is real?", a for-loop has no answer. A three-node StateGraph with named nodes, typed state, and a conditional edge does. The graph IS the slide. Once the decomposition clicked — simulate pops a row, greentpt runs four methods, eval scores and routes — graph.py wrote itself in 22 lines.

**Decision:** LangGraph StateGraph: simulate → greentpt → eval, conditional back-edge, BenchmarkState TypedDict. Judge model isolated in eval_node (separate from GreenPT endpoints).
**GAP → DL-04:** Pipeline runs. Savings formula computes against the wrong denominator.

---

## DL-04 — The formula was wrong
`4 [DL] How should I calculate token savings when each method uses a different baseline.txt`

Smoke run showed 0% savings on a combined row. Combined should be the strongest method — zero on any combined row was the first signal something was broken. The formula was computing savings per-method against itself. A method that produced no client-side compression scored zero even when its output was shorter than baseline. Swapped to cross-method: every row's savings anchored to that row's baseline call. Negative numbers fell out naturally. That's what made the DL-05 and DL-06 findings visible.

**Decision:** `token_savings_pct = (baseline_tokens - method_tokens) / baseline_tokens × 100`. Baseline always 0.0%. Both formulas written to results.csv so any row is hand-verifiable.
**GAP → DL-05:** Formula is correct. Now the data can be read. First finding lands.

---

## DL-05 — GreenPT's own prompt makes it worse
`5 [DL] Does GreenPT's tuned system prompt actually reduce token usage.txt`

The assumption going in: GreenPT's tuned system prompt on green-l would natively produce leaner JSON. The full run broke it. prompt_engineering transmitted 15% MORE tokens than a vanilla extraction prompt at identical quality. Verbosity for nothing. The model's system prompt is tuned for quality — Dutch grammar guardrails, multilingual assistance — not terseness. Not a bug in GreenPT. Just a product design choice that turns "prompt_engineering" from a savings layer into a cost.

**Decision:** Confirmed finding. prompt_engineering never defaults in the router. Memo to GreenPT: add a "be terse" instruction to green-l's system prompt and re-run.
**GAP → DL-06:** prompt_engineering is out. What about combined?

---

## DL-06 — Combined is the quality champion. It's also a liability on short outputs.
`6 [DL] Does the combined method deliver positive savings across all use cases.txt`

The simple pitch: combined stacks both layers, it has to win everywhere. The data broke that too. combined at +32.1% on invoice_parsing. combined at −36.0% on intent_classification. Same method, same run, 68 percentage points apart. The mechanism is mechanical: a fixed ~80-token TOON instruction block prepended to every combined call. On a 12-field nested invoice schema it's overhead amortized. On a {"intent": "..."} output it's bigger than the entire response. The trade only pays when the output is big enough.

**Decision:** Combined is the quality champion (4.29 G-Eval), not the universal savings winner. Route by schema shape: combined for nested/multi-field, postprocess for tiny outputs, never prompt_engineering.
**GAP → DL-07:** Findings are clear. No way to act on them without a smart routing default in the SDK.

---

## DL-07 — The SDK needs a sensible default so no one has to read the report
`7 [DL] Should the SDK force customers to pick a method or auto-route by schema shape.txt`

Forcing every developer to read the benchmark before their first API call is a non-starter. DL-05 and DL-06 just produced the data behind every routing rule. Ship a v0 heuristic now: five lines of Python, zero latency overhead, no LLM call. Plan v1 as a single-function swap once real usage data lands. The pitch quality gap is enormous: without auto-routing the SDK has 4 methods and a tutorial. With it, it has one call.

**Decision:** `smart_route(schema)` in sdk.py. `GreenPTClient(method="auto")` calls it. v0 branches on num_keys, has_arrays, depth, avg_key_len. v0 known bug: prompt_engineering still in the fallback. v1 fixes it.
**GAP → DL-08:** SDK has a default. No one can see it working without a UI.

---

## DL-08 — The playground is what "demo day" actually means
`8 [DL] What is the lowest-friction way to demo GreenPT live to a client.txt`

The CSV and the PDF are evidence. They are not a demo. Every modern API competitor has a playground. The question was how lightweight it could be in half a day. Streamlit and Gradio were faster to write but both produce a data-science tool aesthetic. Flask + vanilla HTML is the only option where the layout is exactly what you build. The transformation was six KPI cards at the top: tokens before, tokens after, savings %, method used, status, latency. Same backend, 50 extra lines of CSS, and the page shifted from debug output to product UI.

**Decision:** Flask + vanilla HTML/CSS/JS at localhost:5000. One command: `python app.py`. Six KPI cards surface the savings number in five seconds. Four collapsible panels for the curious developer.
**GAP → DL-09:** Demo works. The PDF report is how the benchmark travels to people who weren't in the room.

---

## DL-09 — The PDF that regenerates itself
`9 [DL] How do I package benchmark results into an artifact that never goes stale.txt`

A manually-maintained PDF is worse than the CSV — the moment someone copies a number into the doc, there's a transcription error waiting to be discovered at the wrong time. The requirement: one command regenerates everything. reportlab won over Jupyter and weasyprint on operational simplicity. report.py reads results.csv, emits report.pdf and two PNG charts, auto-populates the executive summary from the DataFrame. If the winner changes on a future run, the prose changes with it. The report can never disagree with the charts.

**Decision:** `python report.py` → fresh PDF in under 2 seconds. Executive summary auto-populated. Methodology notes section turns the same charts from "pretty" into "defensible evidence."
**GAP → DL-10:** Report ships. The final number needs a permanent record.

---

## DL-10 — What the data actually says
`10 [DL] What does the full benchmark data actually say about each optimization method.txt`

Every previous DL was upstream of this moment. The headline: postprocess is the quiet winner — +5.6% savings across every use case, zero quality cost, no routing logic needed. combined is the quality champion at 4.31 G-Eval but needs smart routing to avoid the overhead floor. prompt_engineering loses on both axes and should never be a default. 192 rows, 384 API calls, 15 minutes, €0.07. Zero pipeline crashes. The regression baseline for every future GreenPT change.

**Decision:** Log the five numbers. Hand GreenPT two product memos: (1) add "be terse" to green-l's system prompt, (2) move the TOON instruction block server-side so combined is net-positive everywhere.
**Status:** Benchmark complete ✅ — green-r follow-up run pending 🟡

---

*Updated as each DL is completed.*
