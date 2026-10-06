import unittest

from app.database.db import build_db
from app.matching.matcher import Matcher


class MatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = build_db()
        cls.matcher = Matcher(cls.conn)

    def check(self, text, status, product_id=None):
        r = self.matcher.match(text)
        self.assertEqual((r.status, r.product_id), (status, product_id), f"{text!r} -> {r}")

    def test_four_language_styles_resolve_to_p001(self):
        for text in [
            "Where is Dove shampoo?",
            "Dove shampoo எங்கே இருக்கு?",
            "Dove shampoo कहाँ मिलेगा?",
            "Dove shampoo enga irukku?",
            "டவ் ஷாம்பு எங்கே இருக்கு?",
            "डव शैम्पू कहाँ मिलेगा?",
        ]:
            self.check(text, "OK", "P001")

    def test_every_alias_and_name_resolves_to_its_own_product(self):
        pairs = self.conn.execute("SELECT product_id, alias FROM aliases").fetchall()
        pairs += self.conn.execute("SELECT product_id, name FROM products").fetchall()
        for pid, text in pairs:
            self.check("where is " + text, "OK", pid)

    def test_spelling_variation_still_matches(self):
        self.check("colgate tooth paste", "OK", "P002")
        self.check("Coca cola 750 ml please", "OK", "P018")

    def test_partial_name_unique_product(self):
        self.check("kurkure", "OK", "P033")
        self.check("sugar", "OK", "P030")

    def test_ambiguous_asks_to_repeat(self):
        for text in ["dove", "toothpaste", "soap", "tata"]:
            r = self.matcher.match(text)
            self.assertEqual(r.status, "LOW_CONFIDENCE", f"{text!r} -> {r}")

    def test_unknown_product_not_found(self):
        self.check("iphone charger", "NOT_FOUND")

    def test_empty_transcript_asks_to_repeat(self):
        self.check("", "LOW_CONFIDENCE")
        self.check("where is", "LOW_CONFIDENCE")

    def test_confidence_is_reported(self):
        self.assertEqual(self.matcher.match("where is dove shampoo").confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
