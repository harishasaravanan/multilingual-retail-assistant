import unittest

from app.language.normalizer import normalize


class NormalizerTests(unittest.TestCase):
    def test_filler_removed_in_all_styles(self):
        cases = {
            "Where is Dove shampoo?": "dove shampoo",
            "Dove shampoo enga irukku?": "dove shampoo",
            "Dove shampoo எங்கே இருக்கு?": "dove shampoo",
            "Dove shampoo कहाँ मिलेगा?": "dove shampoo",
        }
        for text, query in cases.items():
            self.assertEqual(normalize(text).query, query, text)

    def test_native_script_kept(self):
        self.assertEqual(normalize("டவ் ஷாம்பு எங்கே இருக்கு?").query, "டவ் ஷாம்பு")
        self.assertEqual(normalize("डव शैम्पू कहाँ मिलेगा?").query, "डव शैम्पू")

    def test_empty_and_none(self):
        self.assertEqual(normalize("").query, "")
        self.assertEqual(normalize(None).query, "")
        self.assertEqual(normalize("where is").query, "")

    def test_intent(self):
        self.assertEqual(normalize("Where is Dove shampoo?").intent, "FIND")


if __name__ == "__main__":
    unittest.main()
