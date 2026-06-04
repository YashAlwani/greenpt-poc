"""
GreenPT developer playground — Flask backend.

Run:
    python app.py
    # then open http://localhost:5000

Tabs:
    Playground   — interactive optimizer
    Packets      — live SSE stream of API calls
    Stats        — aggregated results from last benchmark run
    Report       — selective benchmark runner + PDF download
    Explain      — how GreenPT works
"""

import json
import os
import queue
import time

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_file

import events

load_dotenv()

from sdk import smart_route                       # noqa: E402
from tools.greentpt_tools import METHODS          # noqa: E402

app = Flask(__name__, static_folder="static", template_folder="static")

_HERE     = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(_HERE, "outputs")
RESULTS_CSV = os.path.join(OUTPUT_DIR, "results.csv")
REPORT_PDF  = os.path.join(OUTPUT_DIR, "report.pdf")
DATASET_CSV = os.path.join(_HERE, "generated_llm_dataset.csv")

METHOD_ORDER = ["baseline", "postprocess", "prompt_engineering", "combined"]


# ── existing playground endpoint ──────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/optimize", methods=["POST"])
def optimize():
    body = request.get_json(silent=True) or {}
    prompt = (body.get("prompt") or "").strip()
    schema = body.get("schema") or {}
    method = (body.get("method") or "auto").strip()

    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"schema is not valid JSON: {e}"}), 400

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    if not isinstance(schema, dict):
        return jsonify({"error": "schema must be a JSON object"}), 400

    chosen = smart_route(schema) if method == "auto" else method
    if chosen not in METHODS:
        return jsonify({"error": f"unknown method: {chosen}"}), 400

    events.emit({"type": "optimize_start", "method": method, "chosen": chosen, "t": time.time()})

    t0 = time.time()
    result = METHODS[chosen](prompt, schema)
    elapsed = round(time.time() - t0, 2)

    events.emit({"type": "optimize_done", "method": chosen, "savings_pct": result["token_savings_pct"], "elapsed_s": elapsed, "t": time.time()})

    return jsonify({
        "method_requested":  method,
        "method_used":       chosen,
        "elapsed_s":         elapsed,
        "raw_output":        result["raw_output"],
        "toon_output":       result["toon_output"],
        "decoded_output":    result["decoded_output"],
        "key_map":           result["key_map"],
        "tokens_before":     result["tokens_before"],
        "tokens_after":      result["tokens_after"],
        "token_savings_pct": result["token_savings_pct"],
        "status":            result.get("status", "ok"),
    })


# ── SSE stream ────────────────────────────────────────────────────────────────

@app.route("/api/stream")
def stream():
    q = events.subscribe()

    def generate():
        try:
            while True:
                try:
                    payload = q.get(timeout=20)
                    yield f"data: {payload}\n\n"
                except queue.Empty:
                    yield 'data: {"type":"ping"}\n\n'
        except GeneratorExit:
            events.unsubscribe(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── examples for playground dropdown ──────────────────────────────────────────

@app.route("/api/examples")
def examples():
    df = pd.read_csv(DATASET_CSV)
    rows = []
    for _, r in df.iterrows():
        raw_schema = r["expected_output_schema"]
        try:
            schema_obj = json.loads(raw_schema)
        except Exception:
            schema_obj = {}
        rows.append({
            "id":       r["id"],
            "use_case": r["use_case"],
            "size":     r["size"],
            "prompt":   r["prompt"],
            "schema":   schema_obj,
        })
    return jsonify(rows)


# ── stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def stats():
    if not os.path.exists(RESULTS_CSV):
        return jsonify({"error": "no_results"}), 404
    df = pd.read_csv(RESULTS_CSV)
    if df.empty:
        return jsonify({"error": "empty"}), 404

    present = [m for m in METHOD_ORDER if m in df["method"].unique()]

    by_method = (
        df.groupby("method")
        .agg(
            mean_savings=("token_savings_pct", "mean"),
            mean_score=("g_eval_score", "mean"),
            rows=("row_id", "count"),
        )
        .round(2)
        .reindex(present)
        .reset_index()
        .to_dict("records")
    )

    pivot_s = (
        df.pivot_table(index="use_case", columns="method", values="token_savings_pct", aggfunc="mean")
        .round(1)
        .reindex(columns=present)
        .reset_index()
    )
    pivot_q = (
        df.pivot_table(index="use_case", columns="method", values="g_eval_score", aggfunc="mean")
        .round(2)
        .reindex(columns=present)
        .reset_index()
    )

    qf = (
        df.groupby("method")
        .agg(
            quality_warnings=("quality_warning", "sum"),
            parse_failed=("status", lambda s: (s == "parse_failed").sum()),
            api_failed=("status", lambda s: (s == "api_failed").sum()),
            schema_valid=("schema_valid", "sum"),
        )
        .reindex(present)
        .reset_index()
        .to_dict("records")
    )

    return jsonify({
        "methods":        present,
        "by_method":      by_method,
        "pivot_savings":  pivot_s.to_dict("records"),
        "pivot_quality":  pivot_q.to_dict("records"),
        "quality_failures": qf,
        "total_rows":     int(df["row_id"].nunique()) if "row_id" in df.columns else 0,
        "total_results":  len(df),
    })


# ── dataset listing for report page ───────────────────────────────────────────

@app.route("/api/dataset")
def dataset():
    df = pd.read_csv(DATASET_CSV)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "id":             r["id"],
            "use_case":       r["use_case"],
            "size":           r["size"],
            "prompt_preview": str(r["prompt"])[:110] + "…",
        })
    return jsonify(rows)


# ── selective benchmark run + report generation ───────────────────────────────

@app.route("/api/run-report", methods=["POST"])
def run_report():
    body = request.get_json(silent=True) or {}
    selected_ids = body.get("row_ids") or []

    df = pd.read_csv(DATASET_CSV)
    if selected_ids:
        df = df[df["id"].isin(selected_ids)]

    if df.empty:
        return jsonify({"error": "no rows selected"}), 400

    rows  = df.to_dict("records")
    total = len(rows)

    from graph import build_graph   # import after env loaded
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    events.emit({"type": "report_start", "total_rows": total, "t": time.time()})

    graph = build_graph()
    final = graph.invoke(
        {"rows_remaining": rows, "results": []},
        config={"recursion_limit": total * 10 + 50},
    )
    results = final.get("results", [])
    if not results:
        return jsonify({"error": "no results produced"}), 500

    out_df = pd.DataFrame(results)
    out_df.to_csv(RESULTS_CSV, index=False)

    from report import build_pdf
    build_pdf(out_df)

    events.emit({"type": "report_done", "rows_run": total, "results": len(results), "t": time.time()})
    return jsonify({"ok": True, "rows_run": total, "results": len(results)})


# ── PDF download ───────────────────────────────────────────────────────────────

@app.route("/api/download-report")
def download_report():
    if not os.path.exists(REPORT_PDF):
        return jsonify({"error": "No report found. Run a benchmark first."}), 404
    return send_file(REPORT_PDF, as_attachment=True, download_name="greenpt-report.pdf")


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True, use_reloader=False)
