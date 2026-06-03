"""Simulation node — pops the next dataset row and sets it as the current row."""

import json

from state import BenchmarkState


def simulate_node(state: BenchmarkState) -> dict:
    """Pop one row from rows_remaining and populate the current-row fields."""
    rows = state.get("rows_remaining", [])
    if not rows:
        return {}
    current = rows[0]
    remaining = rows[1:]

    # schema may already be a dict or still a JSON string from the CSV
    schema = current.get("expected_output_schema")
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError:
            schema = {}

    print(f"\n[SIM]   row {current.get('id')}  use_case={current.get('use_case')}  size={current.get('size')}")

    return {
        "rows_remaining": remaining,
        "row_id":   current.get("id", ""),
        "use_case": current.get("use_case", ""),
        "size":     current.get("size", ""),
        "prompt":   current.get("prompt", ""),
        "schema":   schema or {},
    }
