from __future__ import annotations

from typing import Any


def topo_sort_nodes(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    node_ids = [str(n["id"]) for n in nodes]
    if len(set(node_ids)) != len(node_ids):
        raise ValueError("Duplicate node ids")

    adj: dict[str, list[str]] = {i: [] for i in node_ids}
    indeg = {i: 0 for i in node_ids}

    for e in edges:
        s = str(e.get("source"))
        t = str(e.get("target"))
        if s not in adj or t not in indeg:
            continue
        adj[s].append(t)
        indeg[t] += 1

    queue = [i for i in node_ids if indeg[i] == 0]
    order: list[str] = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in adj.get(n, []):
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)

    if len(order) != len(node_ids):
        raise ValueError("Workflow graph has a cycle or invalid edges")

    by_id = {str(n["id"]): n for n in nodes}
    return [by_id[i] for i in order]


def parse_flow_definition(
    definition: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = list(definition.get("nodes") or [])
    edges = list(definition.get("edges") or [])
    if not nodes:
        raise ValueError("Workflow definition must include nodes")
    return nodes, edges
