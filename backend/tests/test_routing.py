import unittest

from app.database.db import build_db
from app.routing.router import RouteError, load_graph, shortest_path
from app.service import find_product

EXPECTED = {
    "A1": ["KIOSK", "A1"],
    "A2": ["KIOSK", "A1", "A2"],
    "A3": ["KIOSK", "A1", "A2", "A3"],
    "A4": ["KIOSK", "A1", "A2", "A3", "A4"],
    "A5": ["KIOSK", "A1", "A2", "A3", "A4", "A5"],
    "A6": ["KIOSK", "A1", "A2", "A3", "A4", "A5", "A6"],
    "A7": ["KIOSK", "A1", "A2", "A3", "A4", "A5", "A7"],  # same as API.md example
    "A8": ["KIOSK", "A1", "A2", "A3", "A4", "A5", "A7", "A8"],
}


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = build_db()
        cls.graph = load_graph(cls.conn)

    def test_expected_routes_for_every_node(self):
        for node, path in EXPECTED.items():
            self.assertEqual(shortest_path(self.graph, "KIOSK", node), path, node)

    def test_changing_destination_changes_route(self):
        self.assertNotEqual(find_product(self.conn, "P001")["route"]["nodes"],
                            find_product(self.conn, "P003")["route"]["nodes"])

    def test_every_product_gets_a_route_ending_at_its_node(self):
        ids = [r[0] for r in self.conn.execute("SELECT product_id FROM products")]
        self.assertGreaterEqual(len(ids), 10)
        for pid in ids:
            p = find_product(self.conn, pid)
            self.assertEqual(p["route"]["nodes"][0], "KIOSK")
            self.assertEqual(p["route"]["nodes"][-1], p["node"])
            self.assertEqual(p["route"]["nodes"], EXPECTED[p["node"]], pid)

    def test_start_equals_goal(self):
        self.assertEqual(shortest_path(self.graph, "A3", "A3"), ["A3"])

    def test_unknown_node(self):
        with self.assertRaises(RouteError):
            shortest_path(self.graph, "KIOSK", "Z9")

    def test_disconnected_node(self):
        g = {"KIOSK": {}, "A1": {}}
        with self.assertRaises(RouteError):
            shortest_path(g, "KIOSK", "A1")


class FindProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = build_db()

    def test_matches_api_example(self):
        p = find_product(self.conn, "P001")
        self.assertEqual(set(p), {"product_id", "product", "available", "stock", "price",
                                  "currency", "aisle", "shelf", "x", "y", "node", "route"})
        self.assertEqual(p["route"]["nodes"], ["KIOSK", "A1", "A2", "A3", "A4", "A5", "A7"])
        self.assertEqual(p["route"]["steps"][0], "Walk straight to A1")
        self.assertIn("aisle 7, shelf 3", p["route"]["steps"][-1])

    def test_unknown_product(self):
        self.assertIsNone(find_product(self.conn, "P999"))

    def test_out_of_stock_still_has_route(self):
        pid = self.conn.execute("SELECT product_id FROM products WHERE stock = 0").fetchone()[0]
        p = find_product(self.conn, pid)
        self.assertFalse(p["available"])
        self.assertEqual(p["stock"], 0)
        self.assertGreater(len(p["route"]["nodes"]), 1)


if __name__ == "__main__":
    unittest.main()
