"""
Generate report.pdf from outputs/results.csv.

Usage:
    python report.py
"""

import os
import sys
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_HERE, "outputs")
RESULTS_CSV = os.path.join(OUTPUT_DIR, "results.csv")
REPORT_PDF = os.path.join(OUTPUT_DIR, "report.pdf")
CHART_SAVINGS = os.path.join(OUTPUT_DIR, "chart_savings.png")
CHART_QUALITY = os.path.join(OUTPUT_DIR, "chart_quality.png")

METHOD_ORDER = ["baseline", "postprocess", "prompt_engineering", "combined"]
METHOD_COLORS = {
    "baseline":           "#999999",
    "postprocess":        "#4C9F70",
    "prompt_engineering": "#2E7D32",
    "combined":           "#1B5E20",
}


def _ordered_methods(df: pd.DataFrame):
    present = [m for m in METHOD_ORDER if m in df["method"].unique()]
    return present


def make_charts(df: pd.DataFrame):
    methods = _ordered_methods(df)
    by_method = df.groupby("method").agg(
        savings=("token_savings_pct", "mean"),
        score=("g_eval_score", "mean"),
    ).reindex(methods)

    # Savings chart
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(by_method.index, by_method["savings"], color=[METHOD_COLORS[m] for m in methods])
    ax.set_title("Mean token savings vs baseline (%)", fontsize=13)
    ax.set_ylabel("Savings %")
    ax.axhline(0, color="black", lw=0.6)
    for b, v in zip(bars, by_method["savings"]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}%", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=10)
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(CHART_SAVINGS, dpi=140)
    plt.close()

    # Quality chart
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(by_method.index, by_method["score"], color=[METHOD_COLORS[m] for m in methods])
    ax.set_title("Mean G-Eval score (1–5)", fontsize=13)
    ax.set_ylabel("Score")
    ax.set_ylim(0, 5.5)
    for b, v in zip(bars, by_method["score"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}", ha="center", fontsize=10)
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(CHART_QUALITY, dpi=140)
    plt.close()


def _df_to_table(df: pd.DataFrame, col_widths=None) -> Table:
    data = [list(df.columns)] + df.values.tolist()
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("ALIGN",      (1, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING",(0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    return t


def build_pdf(df: pd.DataFrame):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    make_charts(df)

    doc = SimpleDocTemplate(
        REPORT_PDF,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="GreenPT POC Benchmark Report",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=colors.HexColor("#1B5E20"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.HexColor("#2E7D32"))
    body = styles["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=9, textColor=colors.grey)

    story = []

    # ── Title
    story.append(Paragraph("GreenPT POC — Benchmark Report", h1))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", small))
    story.append(Spacer(1, 0.4 * cm))

    # ── Executive summary
    n_rows = df["row_id"].nunique()
    n_methods = df["method"].nunique()
    by_method = df.groupby("method").agg(
        mean_savings=("token_savings_pct", "mean"),
        mean_score=("g_eval_score", "mean"),
        rows=("row_id", "count"),
    ).reindex(_ordered_methods(df))

    best_method = by_method["mean_savings"].idxmax()
    best_savings = by_method["mean_savings"].max()
    best_score_method = by_method["mean_score"].idxmax()
    best_score = by_method["mean_score"].max()

    summary = (
        f"<b>Scope.</b> {n_rows} dataset rows × {n_methods} methods = {len(df)} scored outputs. "
        f"All methods run against the same underlying compute (Mistral Small 3.2 24B), "
        f"differing only in their optimization layer. "
        f"<br/><br/>"
        f"<b>Headline.</b> <b>{best_method}</b> produced the highest mean token savings "
        f"(<b>{best_savings:.1f}%</b> vs baseline). "
        f"<b>{best_score_method}</b> produced the highest mean G-Eval score "
        f"(<b>{best_score:.2f}/5</b>). "
        f"<br/><br/>"
        f"<b>Methodology.</b> Baseline calls use <font face='Courier'>green-l-raw</font> with a vanilla "
        f"extraction prompt. <font face='Courier'>postprocess</font> applies client-side TOON compression "
        f"on top. <font face='Courier'>prompt_engineering</font> uses <font face='Courier'>green-l</font> "
        f"(GreenPT's tuned system prompt). <font face='Courier'>combined</font> stacks both layers. "
        f"Quality is judged 1–5 by an LLM judge (G-Eval) on schema-validated decoded output."
    )
    story.append(Paragraph(summary, body))
    story.append(Spacer(1, 0.6 * cm))

    # ── Method comparison table
    story.append(Paragraph("Method comparison", h2))
    table_df = by_method.reset_index().rename(columns={
        "method": "Method",
        "mean_savings": "Mean savings %",
        "mean_score": "Mean G-Eval",
        "rows": "Rows",
    })
    table_df["Mean savings %"] = table_df["Mean savings %"].round(1)
    table_df["Mean G-Eval"] = table_df["Mean G-Eval"].round(2)
    story.append(_df_to_table(table_df))
    story.append(Spacer(1, 0.5 * cm))

    # ── Charts
    story.append(Image(CHART_SAVINGS, width=15 * cm, height=8 * cm))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Image(CHART_QUALITY, width=15 * cm, height=8 * cm))

    story.append(PageBreak())

    # ── By use_case × method (savings)
    story.append(Paragraph("Savings by use case", h2))
    pivot_s = df.pivot_table(
        index="use_case", columns="method", values="token_savings_pct", aggfunc="mean"
    ).round(1).reindex(columns=_ordered_methods(df)).reset_index()
    story.append(_df_to_table(pivot_s))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("G-Eval score by use case", h2))
    pivot_q = df.pivot_table(
        index="use_case", columns="method", values="g_eval_score", aggfunc="mean"
    ).round(2).reindex(columns=_ordered_methods(df)).reset_index()
    story.append(_df_to_table(pivot_q))
    story.append(Spacer(1, 0.4 * cm))

    # ── By size
    if "size" in df.columns:
        story.append(Paragraph("Savings by prompt size", h2))
        size_pivot = df.pivot_table(
            index="size", columns="method", values="token_savings_pct", aggfunc="mean"
        ).round(1).reindex(columns=_ordered_methods(df)).reindex(["S", "M", "L"]).reset_index()
        story.append(_df_to_table(size_pivot))
        story.append(Spacer(1, 0.4 * cm))

    # ── Quality / failure analysis
    story.append(Paragraph("Quality &amp; failure breakdown", h2))
    qf = df.groupby("method").agg(
        quality_warnings=("quality_warning", "sum"),
        parse_failed=("status", lambda s: (s == "parse_failed").sum()),
        decode_failed=("status", lambda s: (s == "decode_failed").sum()),
        api_failed=("status", lambda s: (s == "api_failed").sum()),
        schema_valid=("schema_valid", "sum"),
    ).reindex(_ordered_methods(df)).reset_index()
    qf = qf.rename(columns={"method": "Method"})
    story.append(_df_to_table(qf))
    story.append(Spacer(1, 0.4 * cm))

    # ── Methodology notes
    story.append(Paragraph("Methodology notes", h2))
    notes = (
        "<b>Token counting:</b> tiktoken cl100k_base on raw model output (tokens_before) "
        "and on the on-the-wire compressed string (tokens_after). The key_map is treated "
        "as session-level metadata, sent once per session, not per request — matching how a "
        "real proxy would operate."
        "<br/><br/>"
        "<b>Savings %:</b> <font face='Courier'>(baseline_tokens − method_tokens) / baseline_tokens × 100</font>, "
        "computed cross-method per row. <font face='Courier'>baseline</font> is therefore always 0%. "
        "Negative values mean the method transmitted more tokens than the baseline call did "
        "for that row (typically a sign of nondeterminism or model-variant verbosity)."
        "<br/><br/>"
        "<b>Quality floor:</b> rows with G-Eval &lt; 3 are flagged <font face='Courier'>quality_warning</font>. "
        "Flagged but not removed from averages."
        "<br/><br/>"
        "<b>Fairness:</b> temperature=0, max_tokens=1024, identical user prompt across all four methods."
    )
    story.append(Paragraph(notes, body))

    doc.build(story)


def main() -> int:
    if not os.path.exists(RESULTS_CSV):
        print(f"ERROR: {RESULTS_CSV} not found. Run `python run.py` first.")
        return 1
    df = pd.read_csv(RESULTS_CSV)
    if df.empty:
        print("ERROR: results.csv is empty.")
        return 1
    build_pdf(df)
    print(f"Report written: {REPORT_PDF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
