"""Shortest walking route on the store map (SAD section 9, Tier 1).

Links in map_edges are undirected. Tier 2 adds one-way and blocked edges.
"""
import heapq


class RouteError(Exception):
    pass


def load_graph(conn):
    graph = {node: {} for (node,) in conn.execute("SELECT node FROM map_nodes")}
    for a, b, cost in conn.execute("SELECT a, b, cost FROM map_edges"):
        graph[a][b] = cost
        graph[b][a] = cost
    return graph


def shortest_path(graph, start, goal):
    """Dijkstra. Returns the list of nodes from start to goal."""
    for n in (start, goal):
        if n not in graph:
            raise RouteError(f"unknown map node: {n}")
    best = {start: 0.0}
    prev = {}
    heap = [(0.0, start)]
    while heap:
        dist, node = heapq.heappop(heap)
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(prev[path[-1]])
            return path[::-1]
        if dist > best.get(node, float("inf")):
            continue
        for nxt, cost in graph[node].items():
            nd = dist + cost
            if nd < best.get(nxt, float("inf")):
                best[nxt] = nd
                prev[nxt] = node
                heapq.heappush(heap, (nd, nxt))
    raise RouteError(f"no route from {start} to {goal}")


def build_steps(nodes, aisle, shelf):
    steps = []
    for i, node in enumerate(nodes[1:]):
        steps.append(f"Walk straight to {node}" if i == 0 else f"Continue to {node}")
    steps.append(f"You have arrived. Look in aisle {aisle}, shelf {shelf}")
    return steps


def route_to(conn, node, aisle, shelf, start="KIOSK"):
    nodes = shortest_path(load_graph(conn), start, node)
    return {"nodes": nodes, "steps": build_steps(nodes, aisle, shelf)}
