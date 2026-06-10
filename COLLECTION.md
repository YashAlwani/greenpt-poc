# GreenPT POC — Collection Description

**Public Project Repo:** https://github.com/YashAlwani/greenpt-poc

---

## What is this project about?

GreenPT POC is a benchmarking system that measures whether a JSON optimization API actually saves tokens without degrading output quality. Four optimization methods are compared head-to-head across 48 prompts and four real-world use cases — invoice parsing, resume extraction, summarization, and intent classification. The benchmark produces a single defensible number per method: how many tokens does it save, and at what quality cost?

---

## Why does it exist?

GreenPT sells one claim: its optimization layer reduces API token spend without sacrificing output quality. Before that claim can reach a client or CTO, it needs a number they can stress-test. The project was built to produce that number under controlled conditions — same underlying model, temperature locked to zero, failures typed and counted, savings anchored to a shared baseline.

> **Research question:** Does each optimization layer actually do what it says — and when does it stop working?

---

## What was actually accomplished?

A fully working end-to-end benchmark and demo system:

| Component | What it does |
|---|---|
| **LangGraph pipeline** | 3-node graph runs 192 scored outputs across 4 methods |
| **48-row dataset** | Agent-generated source text, hardcoded schemas for reproducibility |
| **G-Eval scoring** | LLM-as-judge quality scoring with an isolated judge model |
| **SDK + smart router** | Picks the right method by schema shape — no config needed |
| **Flask playground** | Shows token savings live with 6 KPI cards |
| **PDF report** | Regenerates from `results.csv` in under 2 seconds |

Two assumptions were falsified by the data:

- `prompt_engineering` sends **15% more tokens** than doing nothing
- `combined` **loses on short outputs** — its fixed 80-token instruction overhead exceeds the entire output for intent classification (-36%)

---

## Phase Story — Day 1 → Day 2

### Day 1 — Research, Rules, and Pipeline

Before any benchmark row ran, two questions had to be answered: what is GreenPT actually doing under the hood, and what does a savings number need to look like to be defensible?

A live system-prompt drop test confirmed that `green-l` silently drops client-provided system prompts — which changed the entire design of the `combined` method. Eight fairness rules were written as **source-code constants** before a single node was built. The 48-row dataset was designed schema-first: hardcoded extraction schemas, agent-generated source text, and a no-op control case included specifically to catch the optimizer hurting where it shouldn't.

The LangGraph pipeline followed: three nodes, a `TypedDict` state contract, a conditional back-edge for the per-row loop. The graph is the methodology diagram — when a client asks how the savings number was produced, the answer is the graph.

| Commit | Description |
|---|---|
| `b92beef` | Initial scaffold |
| `2e3a833` | LangGraph 3-node pipeline |

**DLs produced:** DL-01 (rules) · DL-02 (dataset) · DL-03 (pipeline) · DL-04 (savings formula)

> **What it unlocked:** 192 rows of scored output. Two findings the original assumptions didn't survive.

---

### Day 2 — Findings, SDK, Demo, Report

The full run landed and both headline assumptions broke. `prompt_engineering` was net-negative. `combined` lost 36% on intent classification because a fixed 80-token instruction block is larger than the entire output it's trying to compress. `postprocess` — the unglamorous method — won on savings across every use case with no quality cost.

Those findings fed directly into the SDK: a 25-line routing heuristic that picks the right method by schema shape so no developer has to read the benchmark first. The playground surfaced routing decisions live. The PDF report auto-populated its own executive summary from the DataFrame — if the winner changes on a future run, the prose changes with it.

| Commit | Description |
|---|---|
| `1a9edf6` | PDF report generator |
| `a462241` | Developer playground UI |
| `a970bb4` | Client demo deck |

**DLs produced:** DL-05 (prompt_engineering finding) · DL-06 (combined overhead finding) · DL-07 (SDK routing) · DL-08 (playground) · DL-09 (report) · DL-10 (headline results)

> **What it unlocked:** A client-ready artifact that regenerates from one command, a playground for live demos, and an SDK with a defensible default.

---

## Learning Outcomes Coverage

| LO | Stage | Covered in |
|---|---|---|
| **LO1** | Analyzing | DL-01 · DL-02 · DL-03 · DL-04 · DL-08 |
| **LO2** | Advising | DL-01 · DL-03 · DL-07 · DL-09 |
| **LO3** | Designing | DL-01 · DL-02 · DL-03 · DL-04 · DL-07 · DL-08 · DL-09 |
| **LO4** | Realizing | DL-01 · DL-02 · DL-03 · DL-04 · DL-05 · DL-06 · DL-07 · DL-08 · DL-09 |
| **LO5** | Managing | DL-05 · DL-06 · DL-09 · DL-10 |
