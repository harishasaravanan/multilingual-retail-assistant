import pathlib, tempfile, unittest
from unittest import mock
from fastapi.testclient import TestClient
from app.main import create_app
from app.tts import engine

H = {"Authorization": "Bearer k"}

class TtsRoute(unittest.TestCase):
    def test_serves_cached_file_and_rejects_bad_names(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(engine, "CACHE", pathlib.Path(d)):
            (pathlib.Path(d) / "0123456789abcdef.mp3").write_bytes(b"ID3")
            c = TestClient(create_app(device_token="d", kiosk_token="k"))
            self.assertEqual(c.get("/tts/0123456789abcdef.mp3", headers=H).status_code, 200)
            self.assertEqual(c.get("/tts/0123456789abcdef.mp3").status_code, 401)
            self.assertEqual(c.get("/tts/ffffffffffffffff.mp3", headers=H).status_code, 404)
            self.assertEqual(c.get("/tts/..%2Fmain.py", headers=H).status_code, 404)

    def test_url_only_when_cached(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(engine, "CACHE", pathlib.Path(d)):
            self.assertIsNone(engine.url_for("en", "hello"))
            engine.path_for("en", "hello").write_bytes(b"x")
            self.assertTrue(engine.url_for("en", "hello").startswith("/tts/"))

if __name__ == "__main__":
    unittest.main()
