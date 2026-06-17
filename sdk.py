"""GreenPT developer SDK.

What a third-party app would use:

    from sdk import GreenPTClient

    client = GreenPTClient()                       # auto-routes per schema
    resp = client.call(prompt, schema)
    data = resp.decode()                           # plain dict
    print(resp.method, resp.token_savings_pct)

Or pin a specific method:

    client = GreenPTClient(method="combined")
"""

from toon import collect_keys
from tools.greentpt_tools import METHODS


# ── smart router ──────────────────────────────────────────────────────────────

def _max_depth(obj, level: int = 0) -> int:
    if isinstance(obj, dict):
        return max([_max_depth(v, level + 1) for v in obj.values()] or [level])
    if isinstance(obj, list):
        return max([_max_depth(item, level + 1) for item in obj] or [level])
    return level


def route_with_reason(schema: dict) -> tuple[str, str]:
    """Pick the best method based on schema shape, with a human-readable reason.

    Heuristic v0 — refine after benchmark results land:
      - Tiny schemas (≤2 short keys) → baseline (compression not worth it)
      - Deep / array-heavy schemas → combined (TOON wins on repetition)
      - Schemas with long keys → postprocess (key shortening is the main win)
      - Otherwise → prompt_engineering
    """
    keys = collect_keys(schema)
    num_keys = len(keys)
    if num_keys == 0:
        return "prompt_engineering", "empty schema — defaulting to the tuned model"
    avg_key_len = sum(len(k) for k in keys) / num_keys
    depth = _max_depth(schema)
    schema_str = str(schema).lower()
    has_arrays = "array" in schema_str or any(isinstance(v, list) for v in schema.values())

    if num_keys <= 2 and avg_key_len <= 4:
        return "baseline", "tiny flat schema — compression overhead isn't worth it"
    if has_arrays and depth >= 2:
        return "combined", "deep / array-heavy schema — TOON wins on repetition"
    if avg_key_len > 8:
        return "postprocess", "long key names — client-side key shortening is the main win"
    return "prompt_engineering", "moderate schema — the tuned model handles it"


def smart_route(schema: dict) -> str:
    """Pick the best method based on schema shape. See route_with_reason()."""
    return route_with_reason(schema)[0]


# ── response wrapper ──────────────────────────────────────────────────────────

class TOONResponse:
    """Wraps a method result. .decode() returns the plain dict; .raw() the wire bytes."""

    def __init__(self, run_result: dict):
        self._raw = run_result["toon_output"]
        self._key_map = run_result["key_map"]
        self._decoded = run_result["decoded_output"]
        self.method = run_result["method"]
        self.token_savings_pct = run_result["token_savings_pct"]
        self.tokens_before = run_result["tokens_before"]
        self.tokens_after = run_result["tokens_after"]
        self.status = run_result.get("status", "ok")

    def decode(self) -> dict:
        return self._decoded

    def raw(self) -> str:
        return self._raw

    def key_map(self) -> dict:
        return self._key_map

    def __repr__(self):
        return (
            f"TOONResponse(method={self.method!r}, "
            f"savings={self.token_savings_pct}%, "
            f"tokens={self.tokens_before}→{self.tokens_after}, "
            f"status={self.status!r})"
        )


# ── client ────────────────────────────────────────────────────────────────────

class GreenPTClient:
    """
    Drop-in client for any app. Defaults to smart routing — picks the optimal
    method per schema. Override with `method=` to pin a specific one.

    Example
    -------
        from sdk import GreenPTClient
        client = GreenPTClient()
        resp = client.call(prompt="Extract invoice...", schema={"invoice_number": "string"})
        data = resp.decode()         # → {"invoice_number": "INV-001"}
    """

    SUPPORTED = ("auto", "baseline", "postprocess", "prompt_engineering", "combined")

    def __init__(self, method: str = "auto"):
        if method not in self.SUPPORTED:
            raise ValueError(f"method must be one of {self.SUPPORTED}")
        self.method = method

    def call(self, prompt: str, schema: dict) -> TOONResponse:
        chosen = smart_route(schema) if self.method == "auto" else self.method
        return TOONResponse(METHODS[chosen](prompt, schema))
