"""
GreenPT developer playground — Flask backend.

Run:
    python app.py
    # then open http://localhost:5000

Endpoints:
    GET  /                — serves the playground UI
    POST /api/optimize    — runs one optimization call against GreenPT
                            body: {prompt: str, schema: dict, method: str}
                            returns: full RunResult + smart_route choice
"""

import json
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from sdk import smart_route                     # noqa: E402
from tools.greentpt_tools import METHODS         # noqa: E402

app = Flask(__name__, static_folder="static", template_folder="static")


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

    t0 = time.time()
    result = METHODS[chosen](prompt, schema)
    elapsed = round(time.time() - t0, 2)

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
