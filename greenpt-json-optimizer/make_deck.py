"""
Generate outputs/greenpt_demo.pptx — client-facing presentation deck.

Reads outputs/results.csv (if present) for live numbers and embeds the
charts produced by report.py.

Usage:
    python make_deck.py
"""

import os
import sys

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUTPUT_DIR = r"D:\GreenPT\outputs"
RESULTS_CSV = os.path.join(OUTPUT_DIR, "results.csv")
CHART_SAVINGS = os.path.join(OUTPUT_DIR, "chart_savings.png")
CHART_QUALITY = os.path.join(OUTPUT_DIR, "chart_quality.png")
DECK_PPTX = os.path.join(OUTPUT_DIR, "greenpt_demo.pptx")

# Brand
GREEN_DARK  = RGBColor(0x1B, 0x5E, 0x20)
GREEN_MID   = RGBColor(0x2E, 0x7D, 0x32)
GREEN_LIGHT = RGBColor(0xD8, 0xEC, 0xDE)
GREEN_PALE  = RGBColor(0xF1, 0xF8, 0xF3)
INK         = RGBColor(0x1C, 0x1C, 0x1C)
MUTED       = RGBColor(0x6B, 0x6B, 0x6B)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "Calibri"
MONO = "Consolas"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _bg(slide, color):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid(); bg.fill.fore_color.rgb = color
    bg.line.fill.background()
    bg.shadow.inherit = False
    # send to back
    spTree = bg._element.getparent()
    spTree.remove(bg._element); spTree.insert(2, bg._element)
    return bg


def _text(slide, left, top, width, height, text, *,
          size=18, bold=False, color=INK, font=FONT, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb


def _multiline(slide, left, top, width, height, lines, *,
               size=16, color=INK, font=FONT, bullet=True):
    """lines = [(text, bold?), ...]  — adds one paragraph per entry."""
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(lines):
        if isinstance(item, tuple):
            text, is_bold = item
        else:
            text, is_bold = item, False
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        prefix = "•  " if bullet else ""
        run.text = prefix + text
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = is_bold
        run.font.color.rgb = color
        p.space_after = Pt(8)
    return tb


def _header_bar(slide, title):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.9))
    bar.fill.solid(); bar.fill.fore_color.rgb = GREEN_DARK
    bar.line.fill.background()
    _text(slide, Inches(0.6), Inches(0.18), Inches(12), Inches(0.6),
          title, size=24, bold=True, color=WHITE)
    _text(slide, Inches(11.5), Inches(0.32), Inches(1.6), Inches(0.4),
          "GreenPT", size=13, color=GREEN_LIGHT, align=PP_ALIGN.RIGHT)


def _kpi(slide, left, top, width, label, value, *, color=GREEN_DARK):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, Inches(1.6))
    box.fill.solid(); box.fill.fore_color.rgb = GREEN_PALE
    box.line.color.rgb = GREEN_LIGHT
    _text(slide, left, top + Inches(0.18), width, Inches(0.35),
          label, size=11, color=MUTED, align=PP_ALIGN.CENTER)
    _text(slide, left, top + Inches(0.6), width, Inches(0.9),
          value, size=32, bold=True, color=color, align=PP_ALIGN.CENTER, font=MONO)


def _code_block(slide, left, top, width, height, code, *, size=12):
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xF6, 0xF8, 0xF6)
    box.line.color.rgb = GREEN_LIGHT
    tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15),
                                   width - Inches(0.4), height - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(code.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = line
        run.font.name = MONO
        run.font.size = Pt(size)
        run.font.color.rgb = INK


# ── Slide builders ────────────────────────────────────────────────────────────

def slide_title(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    # Big green block
    block = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(5.5), SLIDE_H)
    block.fill.solid(); block.fill.fore_color.rgb = GREEN_DARK
    block.line.fill.background()
    _text(s, Inches(0.7), Inches(2.6), Inches(4.5), Inches(0.6),
          "▲", size=60, color=WHITE)
    _text(s, Inches(0.7), Inches(3.4), Inches(4.5), Inches(0.6),
          "GreenPT", size=44, bold=True, color=WHITE)
    _text(s, Inches(0.7), Inches(4.2), Inches(4.5), Inches(0.6),
          "Playground & Benchmark POC", size=20, color=GREEN_LIGHT)

    _text(s, Inches(6.2), Inches(2.8), Inches(6.5), Inches(1.0),
          "JSON optimization proxy for LLM APIs",
          size=30, bold=True, color=GREEN_DARK)
    _text(s, Inches(6.2), Inches(3.8), Inches(6.5), Inches(1.0),
          "Cut output tokens 30–60% on JSON-heavy LLM workloads —",
          size=16, color=INK)
    _text(s, Inches(6.2), Inches(4.2), Inches(6.5), Inches(1.0),
          "without sacrificing extraction quality.",
          size=16, color=INK)
    _text(s, Inches(6.2), Inches(5.4), Inches(6.5), Inches(0.5),
          "Drop-in OpenAI-compatible: just change base_url.",
          size=14, color=MUTED, font=MONO)


def slide_problem(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "The problem")
    _multiline(s, Inches(0.7), Inches(1.4), Inches(11.9), Inches(5),
               [
                   ("LLM JSON outputs are wildly redundant.", True),
                   "Every response repeats the same long keys: \"invoice_number\", \"unit_price\", \"line_items\"…",
                   "Whitespace, quoting, indentation — overhead that gets billed per token.",
                   ("In agent loops, the cost compounds.", True),
                   "Each tool result re-enters context as the next call's input.",
                   "A 40% saving on every call stacks across the loop — by call 10 you've avoided thousands of tokens.",
                   ("Developers don't want to rewrite their code.", True),
                   "Any optimization layer has to be a drop-in proxy — same SDK, same prompts, same workflow.",
               ],
               size=16)


def slide_what(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "What GreenPT does")
    _multiline(s, Inches(0.7), Inches(1.4), Inches(11.9), Inches(2),
               [
                   ("Sits between your dev tool and the LLM. Transparent both ways.", True),
               ], size=18, bullet=False)
    # Flow diagram
    flow_y = Inches(2.8)
    boxes = [
        ("Your app",     Inches(0.7),  RGBColor(0xE8, 0xE8, 0xE8)),
        ("GreenPT",      Inches(4.0),  GREEN_DARK),
        ("LLM",          Inches(7.3),  RGBColor(0xE8, 0xE8, 0xE8)),
        ("Your app",     Inches(10.6), RGBColor(0xE8, 0xE8, 0xE8)),
    ]
    for label, x, color in boxes:
        b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, flow_y, Inches(2.4), Inches(1.2))
        b.fill.solid(); b.fill.fore_color.rgb = color
        b.line.color.rgb = GREEN_LIGHT
        text_color = WHITE if color == GREEN_DARK else INK
        _text(s, x, flow_y + Inches(0.35), Inches(2.4), Inches(0.6),
              label, size=18, bold=True, color=text_color, align=PP_ALIGN.CENTER)
    # arrows
    for ax in [Inches(3.1), Inches(6.4), Inches(9.7)]:
        arr = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, ax, flow_y + Inches(0.45), Inches(0.9), Inches(0.3))
        arr.fill.solid(); arr.fill.fore_color.rgb = GREEN_MID
        arr.line.fill.background()
    _text(s, Inches(0.7), Inches(4.4), Inches(11.9), Inches(0.4),
          "Inbound: compress prompts.   Outbound: TOON-compress JSON outputs.   Returns wire format + key_map.",
          size=14, color=MUTED, align=PP_ALIGN.CENTER)

    _multiline(s, Inches(0.7), Inches(5.3), Inches(11.9), Inches(2),
               [
                   ("Two layers of optimization:", True),
                   "1. TOON compression — shorten JSON keys deterministically, strip whitespace",
                   "2. Tuned system prompt — instruct the model to emit lean JSON natively (green-l / green-r tiers)",
               ], size=15)


def slide_integration(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "Drop-in integration")
    _text(s, Inches(0.7), Inches(1.4), Inches(11.9), Inches(0.5),
          "OpenAI-compatible — change two lines:", size=18, bold=True, color=GREEN_DARK)
    _code_block(s, Inches(0.7), Inches(2.1), Inches(5.9), Inches(2.5),
                'from openai import OpenAI\n\n'
                'client = OpenAI(\n'
                '    api_key="YOUR_GREENPT_API_KEY",\n'
                '    base_url="https://api.greenpt.ai/v1",\n'
                ')\n\n'
                '# Use any green-l / green-r model id', size=13)
    _text(s, Inches(6.9), Inches(1.9), Inches(6), Inches(0.5),
          "Or use the GreenPT SDK for auto-routing + decode:", size=15, color=MUTED)
    _code_block(s, Inches(6.9), Inches(2.5), Inches(5.9), Inches(2.5),
                'from sdk import GreenPTClient\n\n'
                'client = GreenPTClient()  # smart routing\n'
                'resp   = client.call(prompt, schema)\n\n'
                'data   = resp.decode()      # normal dict\n'
                'print(resp.token_savings_pct)\n'
                'print(resp.tokens_before, "→", resp.tokens_after)', size=13)
    _multiline(s, Inches(0.7), Inches(5.2), Inches(11.9), Inches(2),
               [
                   "No prompt rewrites. No special LLM features. No retraining.",
                   "Wire format is plain JSON — your existing tooling reads it fine.",
                   ("Compatible with Anthropic, OpenAI, Mistral, Qwen, Llama through Green Router.", True),
               ], size=15)


def slide_methodology(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "How we measured it")
    _multiline(s, Inches(0.7), Inches(1.4), Inches(11.9), Inches(3),
               [
                   ("48-row evaluation set — 4 real use cases × 3 prompt sizes (S/M/L):", True),
                   "invoice_parsing · resume_parsing · summarization · intent_classification",
                   ("Every row run through 4 methods → 192 scored outputs:", True),
                   "baseline (green-l-raw, vanilla prompt) — reference point",
                   "postprocess (green-l-raw + client-side TOON)",
                   "prompt_engineering (green-l, GreenPT's tuned system prompt)",
                   "combined (green-l + client-side TOON)",
               ], size=15)
    _multiline(s, Inches(0.7), Inches(5.0), Inches(11.9), Inches(2),
               [
                   ("Same underlying compute for all four methods.", True),
                   "All run on Mistral Small 3.2 24B. Only the optimization layer changes — isolates GreenPT's value-add.",
                   ("Quality judged 1–5 by an LLM judge (G-Eval) on the decoded output.", True),
               ], size=15)


def slide_results_headline(prs, df):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "Results — headline")

    by_method = df.groupby("method").agg(
        savings=("token_savings_pct", "mean"),
        score=("g_eval_score", "mean"),
    )

    order = ["baseline", "postprocess", "prompt_engineering", "combined"]
    methods = [m for m in order if m in by_method.index]

    # KPI row
    kpi_top = Inches(1.4)
    kpi_w = Inches(2.9)
    spacing = Inches(0.18)
    total_w = kpi_w * 4 + spacing * 3
    start_x = (SLIDE_W - total_w) / 2
    for i, m in enumerate(methods):
        x = start_x + (kpi_w + spacing) * i
        sav = by_method.loc[m, "savings"]
        sav_color = GREEN_DARK if sav > 0 else (RGBColor(0xB3, 0x26, 0x1E) if sav < 0 else MUTED)
        sav_str = f"{sav:+.1f}%" if sav != 0 else "0.0%"
        _kpi(s, x, kpi_top, kpi_w, m, sav_str, color=sav_color)

    # Chart
    if os.path.exists(CHART_SAVINGS):
        s.shapes.add_picture(CHART_SAVINGS, Inches(0.7), Inches(3.3),
                              width=Inches(6.0), height=Inches(3.6))
    if os.path.exists(CHART_QUALITY):
        s.shapes.add_picture(CHART_QUALITY, Inches(6.9), Inches(3.3),
                              width=Inches(6.0), height=Inches(3.6))


def slide_results_per_usecase(prs, df):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "Where each method shines")

    pivot = df.pivot_table(index="use_case", columns="method",
                           values="token_savings_pct", aggfunc="mean").round(1)
    order = ["baseline", "postprocess", "prompt_engineering", "combined"]
    pivot = pivot.reindex(columns=[c for c in order if c in pivot.columns])

    # Build table
    rows = len(pivot) + 1
    cols = len(pivot.columns) + 1
    tbl_left = Inches(0.7); tbl_top = Inches(1.4)
    tbl_width = Inches(11.9); tbl_height = Inches(3.2)
    tbl = s.shapes.add_table(rows, cols, tbl_left, tbl_top, tbl_width, tbl_height).table

    # Header
    tbl.cell(0, 0).text = "use case"
    for j, col in enumerate(pivot.columns):
        tbl.cell(0, j + 1).text = col
    for j in range(cols):
        cell = tbl.cell(0, j)
        cell.fill.solid(); cell.fill.fore_color.rgb = GREEN_DARK
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.color.rgb = WHITE; r.font.bold = True; r.font.size = Pt(13)

    for i, idx in enumerate(pivot.index):
        tbl.cell(i + 1, 0).text = str(idx)
        for j, col in enumerate(pivot.columns):
            val = pivot.loc[idx, col]
            tbl.cell(i + 1, j + 1).text = f"{val:+.1f}%" if val != 0 else "0.0%"
        for j in range(cols):
            cell = tbl.cell(i + 1, j)
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(13)
                    if j == 0:
                        r.font.bold = True

    _multiline(s, Inches(0.7), Inches(5.0), Inches(11.9), Inches(2),
               [
                   ("Invoice & resume parsing: combined wins on both savings and quality.", True),
                   ("Summarization: postprocess delivers steady ~11% savings without quality cost.", True),
                   ("Intent classification: outputs are too small for compression to pay off — TOON instruction overhead bigger than the gain.", True),
                   "→ Smart routing picks the right method per schema automatically.",
               ], size=14)


def slide_live_example(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "Live example — playground")
    _text(s, Inches(0.7), Inches(1.4), Inches(11.9), Inches(0.5),
          "5-key invoice schema, auto routing → postprocess → 48.3% savings in 1.2 s",
          size=15, color=MUTED)

    _text(s, Inches(0.7), Inches(2.2), Inches(5.9), Inches(0.4),
          "Standard JSON output (60 tokens)", size=13, bold=True, color=INK)
    _code_block(s, Inches(0.7), Inches(2.7), Inches(5.9), Inches(2.5),
                '{\n'
                '  "vendor": "BluePeak",\n'
                '  "invoice_number": "INV-001",\n'
                '  "invoice_date": "2026-03-08",\n'
                '  "total_amount": 500,\n'
                '  "currency": "EUR"\n'
                '}', size=12)

    _text(s, Inches(6.9), Inches(2.2), Inches(5.9), Inches(0.4),
          "TOON wire format (31 tokens)", size=13, bold=True, color=GREEN_DARK)
    _code_block(s, Inches(6.9), Inches(2.7), Inches(5.9), Inches(2.5),
                '{"cn":"BluePeak",\n'
                ' "in":"INV-001",\n'
                ' "id":"2026-03-08",\n'
                ' "ta":{"v":500,"c":"EUR"}}\n\n'
                '// key_map sent once per session:\n'
                '// vendor→cn, invoice_number→in, …', size=12)

    _kpi(s, Inches(2.0), Inches(5.4), Inches(2.9), "tokens before", "60", color=INK)
    _kpi(s, Inches(5.2), Inches(5.4), Inches(2.9), "tokens after", "31", color=GREEN_DARK)
    _kpi(s, Inches(8.4), Inches(5.4), Inches(2.9), "savings", "48.3%", color=GREEN_DARK)


def slide_dx(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "The developer experience")
    _multiline(s, Inches(0.7), Inches(1.4), Inches(5.7), Inches(4),
               [
                   ("Three ways to integrate:", True),
                   "Drop-in OpenAI SDK — change base_url, pick a model id, done",
                   "GreenPT SDK — auto-routing + one-line decode of TOON",
                   "Direct HTTP — same OpenAI Chat Completions schema",
                   ("Built-in observability:", True),
                   "Tokens before/after on every response",
                   "Method chosen by smart router",
                   "Failure mode tagged (parse/decode/api)",
               ], size=14)

    _text(s, Inches(6.9), Inches(1.4), Inches(5.9), Inches(0.4),
          "One-liner SDK call:", size=14, bold=True, color=GREEN_DARK)
    _code_block(s, Inches(6.9), Inches(1.9), Inches(5.9), Inches(2.0),
                'resp = GreenPTClient().call(prompt, schema)\n'
                'data = resp.decode()  # plain dict', size=13)
    _text(s, Inches(6.9), Inches(4.1), Inches(5.9), Inches(0.4),
          "Live developer playground:", size=14, bold=True, color=GREEN_DARK)
    _multiline(s, Inches(6.9), Inches(4.5), Inches(5.9), Inches(2.5),
               [
                   "Paste a prompt + schema",
                   "Pick a method or leave on auto",
                   "See tokens before/after + savings live",
                   "Inspect decoded JSON, TOON, key_map, raw output",
               ], size=14)


def slide_next(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, WHITE)
    _header_bar(s, "What's next")
    _multiline(s, Inches(0.7), Inches(1.4), Inches(11.9), Inches(5),
               [
                   ("Smart routing v1 — codify the winners from this benchmark.", True),
                   "Invoice & resume → combined.  Summarization → postprocess.  Intent → baseline.",
                   ("Product follow-up — make green-l's tuned system prompt compression-aware.", True),
                   "Today's data shows green-l is tuned for quality but not for token compression. Easy fix.",
                   ("Benchmark on the reasoning tier (green-r) — does the pattern hold for GPT-OSS?", True),
                   "Same 192-row methodology, ~10 min to run, additional ~€0.10 in API spend.",
                   ("Production rollout — usage analytics + monthly savings reports per customer.", True),
                   "The benchmark pipeline becomes the regression test for every prompt-engineering change.",
               ], size=15)


def slide_close(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, GREEN_DARK)
    _text(s, Inches(0.7), Inches(2.8), Inches(12), Inches(1.2),
          "GreenPT", size=72, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    _text(s, Inches(0.7), Inches(4.0), Inches(12), Inches(0.8),
          "JSON optimization proxy for LLM APIs",
          size=24, color=GREEN_LIGHT, align=PP_ALIGN.CENTER)
    _text(s, Inches(0.7), Inches(5.2), Inches(12), Inches(0.5),
          "api.greenpt.ai/v1", size=16, color=WHITE, align=PP_ALIGN.CENTER, font=MONO)
    _text(s, Inches(0.7), Inches(6.3), Inches(12), Inches(0.4),
          "github.com/YashAlwani/greenpt-poc", size=13, color=GREEN_LIGHT, align=PP_ALIGN.CENTER)


def main() -> int:
    if not os.path.exists(RESULTS_CSV):
        print(f"ERROR: {RESULTS_CSV} not found. Run `python run.py` first.")
        return 1
    df = pd.read_csv(RESULTS_CSV)

    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_title(prs)
    slide_problem(prs)
    slide_what(prs)
    slide_integration(prs)
    slide_methodology(prs)
    slide_results_headline(prs, df)
    slide_results_per_usecase(prs, df)
    slide_live_example(prs)
    slide_dx(prs)
    slide_next(prs)
    slide_close(prs)

    prs.save(DECK_PPTX)
    print(f"Deck written: {DECK_PPTX}  ({len(prs.slides)} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
