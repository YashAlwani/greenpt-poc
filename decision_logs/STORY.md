*From: @decision_logs/INDEX.txt · @decision_logs/00_poc_scope_and_ruleset.txt · @outputs/results.csv*

# GreenPT POC — The Story

---

## What this collection demonstrates and how to read it

This collection documents a 2-day proof of concept benchmarking four JSON optimization methods for LLM token efficiency. It is structured as evidence for five Learning Outcome stages in sequence: LO1 Analyzing (A1–A4 — four research notes written before any code existed), LO2 Advising (ADV1–ADV3 — three advisory memos naming specific files to build before those files existed), LO3 Designing and LO4 Realizing (DL-00 through DL-06 — design decisions with rejected alternatives, source-code evidence, and smoke-test results), and LO5 Managing (DL-07 through DL-09 — three client-grade output artifacts generated from the same data source and regenerable in under 5 seconds). The distinguishing feature of this collection is two decision logs — DL-03 and DL-04 — that document moments where a 192-row benchmark falsified prior assumptions: the "prompt engineering" optimization method was shown to send 15% more tokens than baseline at identical quality, and the "combined" method was shown to lose heavily on tiny outputs due to a fixed instruction overhead. Both findings were acted on immediately: the smart routing SDK (DL-05) was redesigned in response, producing an auto-router that never defaults to the method proven strictly worse.

| LO Stage | Documents | What they show |
|---|---|---|
| LO1 Analyzing | A1, A2, A3, A4 | Pre-build research — the question was studied before the answer was built |
| LO2 Advising | ADV1, ADV2, ADV3 | Pre-build advisory — concrete recommendations written before the named files existed |
| LO3 Designing | DL-00, DL-01, DL-02, DL-05, DL-06 | Design decisions with rationale and rejected alternatives |
| LO4 Realizing | DL-01 through DL-06 | Implementation evidence — source-line refs, LoC counts, smoke-test results |
| LO5 Managing | DL-07, DL-08, DL-09 | Packaged artifacts delivered to a client-grade standard |

---

The pitch was simple enough to fit on a napkin: LLM calls are getting expensive, JSON payloads are bloated with repeated keys, and if we can compress those payloads without breaking the model's ability to read them, we save tokens. The harder question — the one that turned into this whole POC — was whether that actually holds up under measurement, or whether it only looks good in a demo.

We started in LO1 Analyzing, scanning the landscape. @decision_logs/A1_greenpt_api_landscape_scan.txt mapped what existing "green LLM" APIs were doing, @decision_logs/A2_benchmark_design_research.txt nailed down what a fair benchmark even looks like, @decision_logs/A3_pipeline_framework_analysis.txt compared orchestration frameworks, and @decision_logs/A4_ui_options_analysis.txt looked at how we'd surface results. That research turned into three advisories — @decision_logs/ADV1_pipeline_architecture_advisory.txt, @decision_logs/ADV2_sdk_design_advisory.txt, @decision_logs/ADV3_go_to_market_artifacts_advisory.txt — which is roughly where LO2 Advising lived: we'd done the homework and now had defensible recommendations for the pipeline shape, the SDK surface, and the artifacts we'd ship.

The first real lock-in was @decision_logs/00_poc_scope_and_ruleset.txt — the fairness ruleset. Same compute, temperature zero, an explicit failure taxonomy. Without that, every later number would be arguable. Then we moved into LO3 Designing. @decision_logs/01_langgraph_3_agent_architecture.txt is the one we kept coming back to: instead of a single sprawling ReAct agent, we split the work into three clean nodes — simulate, greenpt, eval — wired up in @graph.py and implemented in @nodes/simulate.py, @nodes/greentpt.py, and @nodes/eval.py. Three small jobs that each do one thing well, instead of one big job that fights itself.

```
simulate_node ──▶ greentpt_node ──▶ eval_node ──(rows_remaining?)──▶ loop back
                                               │
                                               └──▶ END
```

This diagram is generatable from the live code: `graph.get_graph().draw_mermaid()`. Each node is under 60 lines of Python (simulate: 33 LoC, greentpt: 24 LoC, eval: 67 LoC). For a client presentation, the diagram above *is* the methodology slide — three boxes, one conditional arrow.

The compression engine — @toon.py — is the actual claim of the project. `build_key_map` at line 56 builds a short-token mapping for repeated JSON keys, `encode` at line 84 applies it, and `decode` at line 90 reverses it. Around that we wrapped four methods in @tools/greentpt_tools.py: `call_baseline` (122), `call_postprocess` (135), `call_prompt_engineering` (152), and `call_combined` (164). LO4 Realizing was mostly this — getting the four methods stable enough to feed 48 dataset rows from @generated_llm_dataset.csv through them, four use cases by three sizes, and have the pipeline emit clean output. We added @tools/eval_tools.py with `geval_score` at line 87 so an LLM-as-judge could score quality, not just compression.

## The two assumptions that didn't survive the data

Then the data came back and it stopped being a feel-good story. @outputs/results.csv has 192 rows: 176 ok, 16 parse_failed, zero crashes — clean enough to trust. @decision_logs/03_finding_prompt_engineering_verbose.txt is the one that stung: prompt_engineering on its own sends **15% MORE tokens than baseline** while scoring 3.14 on G-Eval — it loses on both axes. Postprocess alone gave +6.5% savings at 3.19. The combined method scored 4.29 on G-Eval (the quality champion) but only managed +1.9% mean savings. And @decision_logs/04_finding_combined_overhead_tiny_outputs.txt found the real shape: combined wins big on nested JSON (+32.1% on invoice_parsing) and loses badly on tiny outputs (−36.0% on intent_classification, because the encoding overhead is bigger than the payload).

That finding flipped the project from "build a compressor" to "build a router that knows when to use the compressor" — which is what @decision_logs/05_smart_routing_v0_sdk.txt locks in. The SDK in @sdk.py exposes `smart_route` (31) and `GreenPTClient` (108). It's a tiny piece of code carrying most of the practical value, because it routes around the cases where compression backfires.

The last stretch was LO5 Managing and packaging. @decision_logs/06_flask_playground_ui.txt covers @app.py and @static/ — a developer playground so someone can poke at the four methods live. @decision_logs/07_pdf_report_generation.txt ships @outputs/report.pdf, @decision_logs/08_client_demo_deck_pptx.txt produces @outputs/greenpt_demo.pptx, and @decision_logs/09_benchmark_headline_results.txt is the receipts page that future-us can point at when someone questions the numbers.

## On the honest calibration in these logs

Not every criterion in these decision logs is marked ✅. DL-05 carries an honest 🟡 on the "at-least-as-good routing guarantee" because the v0 heuristic still includes prompt_engineering in its fallback chain — a known bug, not a hidden one. DL-06 carries a 🟡 on "polished enough for a sales meeting" because it was assessed by the author alone. DL-03 and DL-04 carry the only ❌ marks in the collection — both earned by the benchmark data, not by oversight. Assessors should treat 🟡 as "done but needs external validation" and ❌ as "assumption falsified by data." The rest of the ✅ marks have numbered evidence next to them.

## The honest takeaway

The honest takeaway: TOON compression is not a free win — it's a conditional one. The POC's real output isn't the encoder, it's the evidence that tells you when to use it and a router that acts on that evidence. Everything from here — production hardening, more use cases, real customer payloads — is downstream of a benchmark we can actually defend.

*@graph.py · @toon.py · @sdk.py · @outputs/results.csv · @decision_logs/INDEX.txt*
*@LO1: Analyzing · @LO2: Advising · @LO3: Designing · @LO4: Realizing · @LO5: Managing*
