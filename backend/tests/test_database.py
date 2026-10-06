import unittest

from app.database.db import build_db, get_product


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = build_db()

    def test_catalog_size(self):
        n = self.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        self.assertEqual(n, 50)

    def test_every_product_has_aliases(self):
        missing = self.conn.execute(
            "SELECT product_id FROM products WHERE product_id NOT IN"
            " (SELECT product_id FROM aliases)").fetchall()
        self.assertEqual(missing, [])

    def test_every_product_node_exists_on_map(self):
        bad = self.conn.execute(
            "SELECT product_id FROM products WHERE node NOT IN"
            " (SELECT node FROM map_nodes)").fetchall()
        self.assertEqual(bad, [])

    def test_map_is_connected_from_kiosk(self):
        edges = self.conn.execute("SELECT a, b FROM map_edges").fetchall()
        nodes = {r[0] for r in self.conn.execute("SELECT node FROM map_nodes")}
        seen, todo = {"KIOSK"}, ["KIOSK"]
        while todo:
            cur = todo.pop()
            for a, b in edges:
                for x, y in ((a, b), (b, a)):
                    if x == cur and y not in seen:
                        seen.add(y)
                        todo.append(y)
        self.assertEqual(seen, nodes)

    def test_get_product_matches_api_example(self):
        p = get_product(self.conn, "P001")
        self.assertEqual(p["product"], "Dove Shampoo")
        self.assertEqual((p["price"], p["currency"]), (249, "INR"))
        self.assertEqual((p["aisle"], p["shelf"], p["node"]), (7, 3, "A7"))
        self.assertTrue(p["available"])

    def test_unknown_product(self):
        self.assertIsNone(get_product(self.conn, "P999"))

    def test_out_of_stock_product_is_unavailable(self):
        row = self.conn.execute(
            "SELECT product_id FROM products WHERE stock = 0").fetchone()
        self.assertIsNotNone(row, "catalog should include one out-of-stock item for tests")
        p = get_product(self.conn, row[0])
        self.assertFalse(p["available"])
        self.assertEqual(p["stock"], 0)


if __name__ == "__main__":
    unittest.main()
