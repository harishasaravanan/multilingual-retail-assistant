import unittest

from app.database.db import build_db
from app.language.detect import detect_language, reply_language
from app.pipeline import MAX_UTTERANCE_BYTES, ApiError, Pipeline, SessionManager


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = build_db()
        cls.pipeline = Pipeline(cls.conn)

    def run_text(self, text):
        return self.pipeline.process("r_001", text)

    def test_ok_payload(self):
        r = self.run_text("Where is Dove shampoo?")
        self.assertEqual((r["status"], r["product_id"], r["language"], r["reply_language"]),
                         ("OK", "P001", "en", "en"))
        self.assertEqual(r["result"]["price"], 249)
        self.assertIn("aisle 7, shelf 3", r["reply_text"])

    def test_tanglish_replies_in_tamil(self):
        r = self.run_text("Dove shampoo enga irukku?")
        self.assertEqual((r["language"], r["reply_language"]), ("ta-en", "ta"))
        self.assertEqual(r["product_id"], "P001")

    def test_tamil_and_hindi_replies(self):
        t = self.run_text("டவ் ஷாம்பு எங்கே இருக்கு?")
        h = self.run_text("डव शैम्पू कहाँ मिलेगा?")
        self.assertEqual((t["language"], t["reply_language"], t["product_id"]), ("ta", "ta", "P001"))
        self.assertEqual((h["language"], h["reply_language"], h["product_id"]), ("hi", "hi", "P001"))

    def test_spoken_text_uses_same_values_as_result(self):
        for text in ["Where is Dove shampoo?", "Dove shampoo enga irukku?",
                     "डव शैम्पू कहाँ मिलेगा?"]:
            r = self.run_text(text)
            self.assertIn(str(r["result"]["price"]), r["reply_text"])
            self.assertIn(str(r["result"]["aisle"]), r["reply_text"])
            self.assertIn(str(r["result"]["shelf"]), r["reply_text"])

    def test_out_of_stock(self):
        row = self.conn.execute("SELECT product_id, name FROM products WHERE stock = 0").fetchone()
        r = self.run_text("where is " + row["name"])
        self.assertEqual((r["status"], r["product_id"]), ("OUT_OF_STOCK", row["product_id"]))
        self.assertFalse(r["result"]["available"])
        self.assertIn("unavailable", r["reply_text"])

    def test_not_found_and_low_confidence(self):
        nf = self.run_text("iphone charger")
        self.assertEqual((nf["status"], nf["product_id"], nf["result"]), ("NOT_FOUND", None, None))
        lc = self.run_text("toothpaste")
        self.assertEqual((lc["status"], lc["reply_language"]), ("LOW_CONFIDENCE", "en"))
        self.assertEqual(lc["reply_text"], "Sorry, please say that again.")

    def test_language_helpers(self):
        self.assertEqual(detect_language("kahan milega"), "hi")
        self.assertEqual(reply_language("ta-en", "OK"), "ta")
        self.assertEqual(reply_language("hi", "LOW_CONFIDENCE"), "en")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.mgr = SessionManager(Pipeline(build_db()), clock=self.clock)

    def code(self, fn, *args, **kw):
        with self.assertRaises(ApiError) as cm:
            fn(*args, **kw)
        return cm.exception.status_code

    def test_full_flow(self):
        sid = self.mgr.start()["session_id"]
        self.mgr.add_chunk(sid, b"\x00\x01" * 3200)
        out = self.mgr.end(sid, transcript="Where is Dove shampoo?")
        self.assertEqual((out["status"], out["product_id"]), ("OK", "P001"))

    def test_unknown_session(self):
        self.assertEqual(self.code(self.mgr.add_chunk, "s_nope", b"\x00\x00"), 404)
        self.assertEqual(self.code(self.mgr.end, "s_nope"), 404)

    def test_second_end_is_gone(self):
        sid = self.mgr.start()["session_id"]
        self.mgr.end(sid, transcript="sugar")
        self.assertEqual(self.code(self.mgr.end, sid), 410)
        self.assertEqual(self.code(self.mgr.add_chunk, sid, b"\x00\x00"), 410)

    def test_session_expires_after_10_seconds(self):
        sid = self.mgr.start()["session_id"]
        self.clock.t = 10.5
        self.assertEqual(self.code(self.mgr.add_chunk, sid, b"\x00\x00"), 410)

    def test_chunk_resets_the_timeout(self):
        sid = self.mgr.start()["session_id"]
        self.clock.t = 8
        self.mgr.add_chunk(sid, b"\x00\x00")
        self.clock.t = 16
        self.mgr.add_chunk(sid, b"\x00\x00")

    def test_bad_audio(self):
        sid = self.mgr.start()["session_id"]
        self.assertEqual(self.code(self.mgr.add_chunk, sid, b"\x00"), 422)
        self.assertEqual(self.code(self.mgr.add_chunk, sid, b"\x00\x00" * 40000), 422)

    def test_utterance_length_limit(self):
        sid = self.mgr.start()["session_id"]
        chunk = b"\x00\x00" * 16000
        for _ in range(MAX_UTTERANCE_BYTES // len(chunk)):
            self.mgr.add_chunk(sid, chunk)
        self.assertEqual(self.code(self.mgr.add_chunk, sid, chunk), 422)

    def test_no_stt_returns_error_status(self):
        sid = self.mgr.start()["session_id"]
        out = self.mgr.end(sid)
        self.assertEqual((out["status"], out["result"], out["reply_language"]), ("ERROR", None, "en"))

    def test_stt_failure_returns_error_status(self):
        def broken(_audio):
            raise RuntimeError("stt down")
        mgr = SessionManager(Pipeline(build_db()), stt=broken, clock=self.clock)
        sid = mgr.start()["session_id"]
        self.assertEqual(mgr.end(sid)["status"], "ERROR")

    def test_stt_hook_is_used(self):
        mgr = SessionManager(Pipeline(build_db()), stt=lambda audio: "Where is Dove shampoo?",
                             clock=self.clock)
        sid = mgr.start()["session_id"]
        mgr.add_chunk(sid, b"\x00\x00")
        self.assertEqual(mgr.end(sid)["product_id"], "P001")


if __name__ == "__main__":
    unittest.main()
