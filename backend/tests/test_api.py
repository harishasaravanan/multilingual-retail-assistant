"""HTTP-level tests. Skipped automatically if fastapi is not installed."""
import unittest

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("fastapi/httpx not installed")

from app.main import create_app

DEVICE = {"Authorization": "Bearer dev-device"}
KIOSK = {"Authorization": "Bearer dev-kiosk"}
PCM = b"\x00\x01" * 3200


def make_client(**kw):
    app = create_app(device_token="dev-device", kiosk_token="dev-kiosk", **kw)
    return TestClient(app), app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client, self.app = make_client(dev_transcript=True)

    def start(self):
        r = self.client.post("/voice-query/start", headers=DEVICE)
        self.assertEqual(r.status_code, 200)
        return r.json()["session_id"]

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual((r.status_code, r.json()), (200, {"status": "up"}))

    def test_auth_is_required_and_tokens_are_separate(self):
        self.assertEqual(self.client.post("/voice-query/start").status_code, 401)
        self.assertEqual(self.client.post("/voice-query/start", headers=KIOSK).status_code, 401)
        r = self.client.post("/find-product", headers=DEVICE, json={"product_id": "P001"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"], "UNAUTHORIZED")
        self.assertIn("request_id", r.json())
        self.assertEqual(self.client.get("/kiosk/events").status_code, 401)
        self.assertEqual(self.client.get("/kiosk/events", headers=DEVICE).status_code, 401)

    def test_full_voice_flow(self):
        sid = self.start()
        c = self.client.post(f"/voice-query/{sid}/chunk", headers=DEVICE, content=PCM)
        self.assertEqual(c.status_code, 204)
        e = self.client.post(f"/voice-query/{sid}/end", headers=DEVICE,
                             json={"transcript": "Dove shampoo enga irukku?"})
        self.assertEqual(e.status_code, 200)
        body = e.json()
        self.assertEqual((body["status"], body["product_id"], body["language"],
                          body["reply_language"]), ("OK", "P001", "ta-en", "ta"))
        self.assertEqual(body["result"]["route"]["nodes"][0], "KIOSK")
        for key in ("request_id", "confidence", "reply_text", "tts_audio_url"):
            self.assertIn(key, body)

    def test_session_errors(self):
        h = DEVICE
        r = self.client.post("/voice-query/s_nope/chunk", headers=h, content=PCM)
        self.assertEqual((r.status_code, r.json()["error"]), (404, "UNKNOWN_SESSION"))
        sid = self.start()
        r = self.client.post(f"/voice-query/{sid}/chunk", headers=h, content=b"\x00")
        self.assertEqual((r.status_code, r.json()["error"]), (422, "INVALID_AUDIO"))
        self.client.post(f"/voice-query/{sid}/end", headers=h, json={"transcript": "sugar"})
        r = self.client.post(f"/voice-query/{sid}/end", headers=h, json={"transcript": "sugar"})
        self.assertEqual((r.status_code, r.json()["error"]), (410, "SESSION_EXPIRED"))

    def test_bad_transcript_body(self):
        sid = self.start()
        r = self.client.post(f"/voice-query/{sid}/end", headers=DEVICE, content=b"not json")
        self.assertEqual((r.status_code, r.json()["error"]), (422, "INVALID_BODY"))

    def test_without_dev_flag_and_no_stt_the_status_is_error(self):
        client, _ = make_client(dev_transcript=False)
        sid = client.post("/voice-query/start", headers=DEVICE).json()["session_id"]
        r = client.post(f"/voice-query/{sid}/end", headers=DEVICE,
                        json={"transcript": "Dove shampoo"})
        self.assertEqual((r.status_code, r.json()["status"]), (200, "ERROR"))

    def test_find_product(self):
        r = self.client.post("/find-product", headers=KIOSK,
                             json={"product_id": "P001", "language": "ta-en"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual((body["product"], body["price"], body["currency"]),
                         ("Dove Shampoo", 249, "INR"))
        self.assertEqual(body["route"]["nodes"], ["KIOSK", "A7"])

    def test_find_product_errors(self):
        r = self.client.post("/find-product", headers=KIOSK, json={"product_id": "P999"})
        self.assertEqual((r.status_code, r.json()["error"]), (404, "UNKNOWN_PRODUCT"))
        r = self.client.post("/find-product", headers=KIOSK, json={"nope": 1})
        self.assertEqual((r.status_code, r.json()["error"]), (422, "INVALID_BODY"))
        r = self.client.post("/find-product", headers=KIOSK, content=b"garbage")
        self.assertEqual((r.status_code, r.json()["error"]), (422, "INVALID_BODY"))

    def test_kiosk_screens_are_told_about_each_step(self):
        q = self.app.state.broker.subscribe()
        sid = self.start()
        self.client.post(f"/voice-query/{sid}/end", headers=DEVICE,
                         json={"transcript": "Where is Dove shampoo?"})
        events = []
        while not q.empty():
            events.append(q.get_nowait()[0])
        self.assertEqual(events, ["state", "state", "result"])


if __name__ == "__main__":
    unittest.main()
