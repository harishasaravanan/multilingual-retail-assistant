import unittest
from app.cart import Cart
from app.database.db import build_db


class CartTests(unittest.TestCase):
    def test_cart_and_route(self):
        c = Cart(build_db())
        self.assertTrue(c.add("P001"))
        self.assertTrue(c.add("P003"))
        self.assertFalse(c.add("NOPE"))
        r = c.route()
        avail_nodes = {i["node"] for i in c.items() if i["available"]}
        self.assertEqual(sorted(r["order"]), sorted(avail_nodes))
        self.assertEqual(r["path"][0], "KIOSK")
        self.assertEqual(r["path"][-1], r["order"][-1])
        c.clear()
        self.assertEqual(c.route()["order"], [])
