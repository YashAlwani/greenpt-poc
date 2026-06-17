"""
TOON engine — JSON compression for GreenPT.

Compress:  compress(obj) -> (toon_str, key_map)
Expand:    decode(toon_str, key_map) -> dict
"""

import json
import re


def collect_keys(obj, seen=None):
    """Depth-first walk; return unique keys in first-seen order."""
    if seen is None:
        seen = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in seen:
                seen.append(k)
            collect_keys(v, seen)
    elif isinstance(obj, list):
        for item in obj:
            collect_keys(item, seen)
    return seen


def _candidate(key):
    """First letter of each underscore/camelCase segment."""
    parts = re.split(r"[_\-]", key)
    if len(parts) == 1:
        # camelCase split
        parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", key) or [key]
    return "".join(p[0].lower() for p in parts if p)


def make_abbreviation(key, registry):
    """Return a collision-free abbreviation. Mutates registry {abbrev -> original}."""
    base = _candidate(key) or key[0].lower()
    candidate = base
    suffix = 2
    while candidate in registry and registry[candidate] != key:
        # extend: try first 2 chars of key, then first 3, then base+suffix
        if len(key) >= suffix:
            candidate = key[:suffix].lower()
            suffix += 1
        else:
            candidate = f"{base}{suffix}"
            suffix += 1
    registry[candidate] = key
    return candidate


MIN_KEY_LEN_TO_ABBREVIATE = 4  # keys ≤3 chars stay as-is — no compression benefit


def build_key_map(obj):
    """Return {original_key: abbreviation} for keys long enough to compress.

    Keys with ≤3 chars are omitted (passed through unchanged via .get(k, k)
    in _substitute). Iteration order is deterministic (depth-first, first-seen).
    """
    keys = collect_keys(obj)
    registry = {}  # abbrev -> original (collision tracker)
    key_map = {}   # original -> abbrev (only for keys we actually shorten)
    for k in keys:
        if len(k) < MIN_KEY_LEN_TO_ABBREVIATE:
            continue
        abbrev = make_abbreviation(k, registry)
        # don't bother if abbreviation isn't shorter than the original
        if len(abbrev) < len(k):
            key_map[k] = abbrev
    return key_map


def _substitute(obj, key_map):
    """Recursively replace dict keys using key_map."""
    if isinstance(obj, dict):
        return {key_map.get(k, k): _substitute(v, key_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(item, key_map) for item in obj]
    return obj


def encode(obj, key_map):
    """Substitute keys then serialize without whitespace."""
    compressed = _substitute(obj, key_map)
    return json.dumps(compressed, separators=(",", ":"), ensure_ascii=False)


def decode(toon_str, key_map):
    """Reverse key_map and restore original keys."""
    inverted = {v: k for k, v in key_map.items()}
    obj = json.loads(toon_str)
    return _substitute(obj, inverted)


def compress(obj):
    """One-call entry point. Returns (toon_string, key_map)."""
    if isinstance(obj, str):
        obj = json.loads(obj)
    key_map = build_key_map(obj)
    toon_str = encode(obj, key_map)
    return toon_str, key_map


if __name__ == "__main__":
    sample = {
        "invoice_number": "INV-001",
        "total_amount": 999.99,
        "line_items": [{"description": "Widget", "unit_price": 10.0}],
    }
    toon_str, km = compress(sample)
    restored = decode(toon_str, km)
    assert restored == sample, f"Round-trip failed: {restored}"
    print("TOON round-trip OK")
    print("Compressed :", toon_str)
    print("Key map    :", km)
    original_len = len(json.dumps(sample, separators=(",", ":")))
    compressed_len = len(toon_str)
    print(f"Savings    : {(original_len - compressed_len) / original_len * 100:.1f}%")
