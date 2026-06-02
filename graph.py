"""LangGraph wiring for the benchmark pipeline."""

from langgraph.graph import END, StateGraph

from nodes.eval import eval_node, should_continue
from nodes.greentpt import greentpt_node
from nodes.simulate import simulate_node
from state import BenchmarkState


def build_graph():
    g = StateGraph(BenchmarkState)
    g.add_node("simulate", simulate_node)
    g.add_node("greentpt", greentpt_node)
    g.add_node("eval",     eval_node)

    g.set_entry_point("simulate")
    g.add_edge("simulate", "greentpt")
    g.add_edge("greentpt", "eval")
    g.add_conditional_edges("eval", should_continue, {"simulate": "simulate", END: END})

    return g.compile()
