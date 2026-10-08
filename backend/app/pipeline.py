"""Voice-query pipeline and session handling behind the /voice-query endpoints.

Pure Python so it can be tested without a web server. The FastAPI layer only
translates HTTP to these calls and ApiError to status codes.
"""
import itertools
import time

from app.language.detect import detect_language, reply_language
from app.matching.matcher import Matcher
from app.service import find_product
from app.tts.replies import build_reply, spoken_language
from app.tts.engine import url_or_generate

SESSION_TIMEOUT_S = 10
MAX_UTTERANCE_BYTES = 15 * 16000 * 2  # 15 s of 16 kHz 16-bit mono
MAX_CHUNK_BYTES = 64 * 1024


def _log_timing(rid, stt_s, proc_s):
    import pathlib
    d = pathlib.Path(__file__).resolve().parents[2] / "results" / "latency"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "latency.csv"
    new = not f.exists()
    with f.open("a") as fh:
        if new:
            fh.write("request_id,stt_s,process_s,total_s\n")
        fh.write(f"{rid},{stt_s:.3f},{proc_s:.3f},{stt_s + proc_s:.3f}\n")
    return {"stt_s": round(stt_s, 3), "process_s": round(proc_s, 3)}


class ApiError(Exception):
    def __init__(self, status_code, error, message):
        super().__init__(message)
        self.status_code, self.error, self.message = status_code, error, message


class Pipeline:
    def __init__(self, conn):
        self.conn = conn
        self.matcher = Matcher(conn)

    def process(self, request_id, transcript):
        """Transcript text -> the /voice-query/{id}/end response body."""
        language = detect_language(transcript)
        m = self.matcher.match(transcript)
        status, result, product_id = m.status, None, None
        if m.status == "OK":
            result = find_product(self.conn, m.product_id)
            product_id = m.product_id
            if not result["available"]:
                status = "OUT_OF_STOCK"
        else:
            result = None
        rl = reply_language(language, status)
        text = build_reply(status, rl, result)
        return {
            "request_id": request_id,
            "status": status,
            "language": language,
            "reply_language": rl,
            "product_id": product_id,
            "confidence": m.confidence,
            "result": result,
            "reply_text": text,
            "tts_audio_url": url_or_generate(spoken_language(status, rl), text),
        }

    def error(self, request_id):
        return {
            "request_id": request_id, "status": "ERROR", "language": "en",
            "reply_language": "en", "product_id": None, "confidence": None, "result": None,
            "reply_text": build_reply("ERROR", "en"),
            "tts_audio_url": url_or_generate("en", build_reply("ERROR", "en")),
        }


class SessionManager:
    def __init__(self, pipeline, stt=None, clock=time.monotonic):
        """stt: optional callable(audio_bytes) -> transcript text. None until STT is wired."""
        self.pipeline, self.stt, self.clock = pipeline, stt, clock
        self._sessions = {}
        self._ids = itertools.count(1)

    def _request_id(self):
        return f"r_{next(self._ids):03d}"

    def start(self):
        n = next(self._ids)
        sid = f"s_{n:04x}"
        self._sessions[sid] = {"audio": bytearray(), "last": self.clock(), "ended": False}
        return {"session_id": sid, "request_id": f"r_{n:03d}"}

    def _get(self, sid):
        s = self._sessions.get(sid)
        if s is None:
            raise ApiError(404, "UNKNOWN_SESSION", f"Unknown session {sid}")
        if s["ended"]:
            raise ApiError(410, "SESSION_EXPIRED", f"Session {sid} already ended")
        if self.clock() - s["last"] > SESSION_TIMEOUT_S:
            s["ended"] = True
            raise ApiError(410, "SESSION_EXPIRED", f"Session {sid} expired")
        return s

    def check(self, sid):
        """Raise ApiError unless the session exists and is still open."""
        self._get(sid)

    def add_chunk(self, sid, data):
        s = self._get(sid)
        if len(data) % 2 or len(data) > MAX_CHUNK_BYTES:
            raise ApiError(422, "INVALID_AUDIO", "Chunk must be 16-bit PCM, at most 64 KB")
        if len(s["audio"]) + len(data) > MAX_UTTERANCE_BYTES:
            raise ApiError(422, "INVALID_AUDIO", "Utterance longer than 15 s")
        s["audio"].extend(data)
        s["last"] = self.clock()

    def end(self, sid, transcript=None):
        """transcript: development override that skips STT. Remove once real STT is in."""
        s = self._get(sid)
        s["ended"] = True
        rid = self._request_id()
        try:
            if transcript is None:
                if self.stt is None:
                    raise RuntimeError("no STT configured")
                _t0 = time.perf_counter(); transcript = self.stt(bytes(s["audio"])); self.last_stt = time.perf_counter() - _t0
            _t1 = time.perf_counter(); out = self.pipeline.process(rid, transcript)
            out["timings"] = _log_timing(rid, getattr(self, "last_stt", 0.0), time.perf_counter() - _t1)
            self.last_stt = 0.0
            return out
        except Exception:
            return self.pipeline.error(rid)
