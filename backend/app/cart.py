import itertools
from app.routing.router import load_graph, shortest_path
from app.service import find_product


class Cart:
    """Single-kiosk, in-memory cart."""
    def __init__(self, conn):
        self.conn, self.ids = conn, []

    def add(self, pid):
        if find_product(self.conn, pid) is None:
            return False
        if pid not in self.ids:
            self.ids.append(pid)
        return True

    def remove(self, pid):
        if pid in self.ids:
            self.ids.remove(pid)

    def clear(self):
        self.ids = []

    def items(self):
        out = []
        for pid in self.ids:
            r = find_product(self.conn, pid)
            out.append({"product_id": pid, "product": r["product"], "available": r["available"],
                        "aisle": r["aisle"], "shelf": r["shelf"], "node": r["node"]})
        return out

    def route(self):
        items = self.items()
        avail = [i for i in items if i["available"]]
        skipped = [i["product"] for i in items if not i["available"]]
        nodes = sorted({i["node"] for i in avail})
        g = load_graph(self.conn)
        pts = ["KIOSK"] + nodes
        paths, dist = {}, {}
        for a in pts:
            for b in pts:
                if a != b:
                    p = shortest_path(g, a, b)
                    paths[a, b] = p
                    dist[a, b] = sum(g[x][y] for x, y in zip(p, p[1:]))
        if len(nodes) <= 8:  # exact: at most 8! orders
            best = min(itertools.permutations(nodes), key=lambda perm: sum(
                dist[a, b] for a, b in zip(("KIOSK",) + perm, perm)), default=())
            order = list(best)
        else:  # nearest neighbour for bigger maps
            order, cur, left = [], "KIOSK", set(nodes)
            while left:
                cur = min(left, key=lambda n: dist[cur, n])
                order.append(cur)
                left.discard(cur)
        path, cur, total = ["KIOSK"], "KIOSK", 0.0
        for n in order:
            path += paths[cur, n][1:]
            total += dist[cur, n]
            cur = n
        stops = [{"node": n, "items": [{"product": i["product"], "aisle": i["aisle"], "shelf": i["shelf"]}
                                       for i in avail if i["node"] == n]} for n in order]
        return {"order": order, "path": path, "stops": stops, "skipped": skipped,
                "total_cost": round(total, 1)}
