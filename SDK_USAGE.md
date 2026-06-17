# GreenPT SDK — Usage Guide

A thin client for GreenPT's token-reduction layer. You hand it a `prompt` and the
`schema` you expect back; it picks an optimization method, calls GreenPT's
OpenAI-compatible endpoint, and returns a response you can decode straight to a dict.

## Install & configure

```bash
pip install -r requirements.txt
echo "GREENPT_API_KEY=sk-..." > .env      # read via python-dotenv / os.environ
```

The client reads `GREENPT_API_KEY` from the environment at import time.

## Quick start

```python
from dotenv import load_dotenv; load_dotenv()
from sdk import GreenPTClient

client = GreenPTClient()                      # auto-routes per schema shape
resp = client.call(
    prompt="Extract invoice fields from the text and return JSON …",
    schema={"vendor": "string", "invoice_number": "string", "total_amount": "number"},
)

data = resp.decode()          # → plain dict with full field names
print(resp.method, resp.token_savings_pct, resp.status)
```

## Pinning a method

`auto` is the default. Pin a specific method when you want deterministic behavior:

```python
client = GreenPTClient(method="combined")     # always maximum compression
resp = client.call(prompt, schema)
```

Valid values: `"auto"`, `"baseline"`, `"postprocess"`, `"prompt_engineering"`,
`"combined"`. An unknown value raises `ValueError` at construction.

## Methods

| Method | Model | What it does |
|---|---|---|
| `baseline` | `green-l-raw` | No optimization — the reference point. |
| `postprocess` | `green-l-raw` | Normal call, then TOON-compress the response client-side. |
| `prompt_engineering` | `green-l` | GreenPT's tuned model returns lean JSON natively. |
| `combined` | `green-l` | Tuned model **plus** TOON key-shortening. Max reduction. |

## Smart routing

With `method="auto"`, the client inspects the schema and picks a method. You can
inspect the decision without making a call:

```python
from sdk import route_with_reason

route_with_reason({"id": "string", "qty": "number"})
# → ('baseline', "tiny flat schema — compression overhead isn't worth it")

route_with_reason({"title": "string", "tags": ["string"],
                   "sections": [{"heading": "string"}]})
# → ('combined', 'deep / array-heavy schema — TOON wins on repetition')
```

Routing heuristics (v0 — tune after benchmark results):

| Schema shape | Routed to |
|---|---|
| Tiny flat (≤2 short keys) | `baseline` |
| Deep / array-heavy | `combined` |
| Long key names (avg > 8 chars) | `postprocess` |
| Everything else | `prompt_engineering` |

## The response object — `TOONResponse`

```python
resp.decode()            # dict — full field names restored (what your app uses)
resp.raw()               # str  — the compressed on-wire JSON string
resp.key_map()           # dict — {original_key: abbreviation} used for this call
resp.method              # str  — the method actually used (after routing)
resp.token_savings_pct   # float — client-side (raw → wire) compression for this call
resp.tokens_before       # int  — tokens in the raw model output
resp.tokens_after        # int  — tokens on the wire (after TOON)
resp.status              # "ok" | "parse_failed" | "decode_failed" | "api_failed"
```

> **Note on `token_savings_pct`:** on the response object this is the method's own
> raw → wire compression, not savings versus a baseline call. For the headline
> "savings vs baseline" number, run the benchmark pipeline (Report/Stats), which
> compares each method's wire tokens against an actual `baseline` call.

## Handling failures

The SDK never raises on a bad model response — check `status` instead:

```python
resp = client.call(prompt, schema)
if resp.status != "ok":
    # api_failed → network/auth; parse_failed → model didn't return JSON
    log.warning("greenpt %s: %s", resp.method, resp.status)
    data = {}                      # decode() returns {} on non-ok status
else:
    data = resp.decode()
```

## End-to-end example

```python
from dotenv import load_dotenv; load_dotenv()
from sdk import GreenPTClient

client = GreenPTClient()           # auto
resp = client.call(
    prompt=(
        "Generate article metadata for the text and return JSON.\n"
        "---\nThe European grid passed a renewable milestone this quarter.\n---\n"
        "Return ONLY valid JSON matching the schema."
    ),
    schema={
        "title": "string",
        "summary": "string",
        "tags": ["string"],
        "sections": [{"heading": "string", "word_count": "number"}],
    },
)

print(resp)                        # TOONResponse(method='combined', savings=…, …)
print(resp.decode())               # {'title': …, 'tags': [...], 'sections': [...]}
```
