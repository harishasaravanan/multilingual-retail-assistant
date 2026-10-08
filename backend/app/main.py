"""FastAPI layer for API.md v1.1. Logic lives in pipeline.py, service.py and events.py.

Run (development, localhost only):
    cd backend
    export MRA_DEVICE_TOKEN=dev-device MRA_KIOSK_TOKEN=dev-kiosk MRA_DEV_TRANSCRIPT=1
    uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
"""
import hmac
import json
import os
import re
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.database.db import build_db
from app.events import Broker, event_stream
from app.pipeline import ApiError, Pipeline, SessionManager
from app.service import find_product
from app.tts import engine


def _rid():
    return "r_" + uuid.uuid4().hex[:6]


def _bearer_ok(request, expected):
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(token.encode(), expected.encode())


def create_app(device_token=None, kiosk_token=None, conn=None, stt=None, dev_transcript=None):
    device_token = device_token or os.environ.get("MRA_DEVICE_TOKEN")
    kiosk_token = kiosk_token or os.environ.get("MRA_KIOSK_TOKEN")
    if not device_token or not kiosk_token:
        raise RuntimeError("Set MRA_DEVICE_TOKEN and MRA_KIOSK_TOKEN before starting the backend")
    if dev_transcript is None:
        dev_transcript = os.environ.get("MRA_DEV_TRANSCRIPT") == "1"

    if stt is None and os.environ.get("MRA_STT") == "whisper":
        from app import stt_whisper
        stt_whisper._get()  # load the model at startup (about 17 s)
        stt = stt_whisper.transcribe

    conn = conn or build_db()  # in-memory DB seeded from database/*.csv
    pipeline = Pipeline(conn)
    sessions = SessionManager(pipeline, stt=stt)
    broker = Broker()

    app = FastAPI(title="Multilingual Retail Assistant", version="1.1")
    app.state.broker = broker
    app.state.sessions = sessions

    @app.exception_handler(ApiError)
    async def api_error(_request, exc):
        return JSONResponse(status_code=exc.status_code, content={
            "request_id": _rid(), "error": exc.error, "message": exc.message})

    @app.exception_handler(RequestValidationError)
    async def bad_request(_request, exc):
        return JSONResponse(status_code=422, content={
            "request_id": _rid(), "error": "INVALID_BODY", "message": "Invalid request"})

    def need_device(request):
        if not _bearer_ok(request, device_token):
            raise ApiError(401, "UNAUTHORIZED", "Missing or bad device token")

    def need_kiosk(request):
        if not _bearer_ok(request, kiosk_token):
            raise ApiError(401, "UNAUTHORIZED", "Missing or bad kiosk token")

    @app.get("/health")
    async def health():
        return {"status": "up"}

    @app.post("/voice-query/start")
    async def start(request: Request):
        need_device(request)
        out = sessions.start()
        broker.publish("state", {"state": "listening"})
        return out

    @app.post("/voice-query/{session_id}/chunk")
    async def chunk(session_id: str, request: Request):
        need_device(request)
        sessions.add_chunk(session_id, await request.body())
        return Response(status_code=204)

    @app.post("/voice-query/{session_id}/end")
    async def end(session_id: str, request: Request):
        need_device(request)
        transcript = None
        if dev_transcript:  # development only: skip STT with {"transcript": "..."}
            raw = await request.body()
            if raw:
                try:
                    transcript = json.loads(raw)["transcript"]
                except (ValueError, KeyError, TypeError):
                    raise ApiError(422, "INVALID_BODY", 'Expected {"transcript": "..."}')
        sessions.check(session_id)
        broker.publish("state", {"state": "processing"})
        payload = sessions.end(session_id, transcript=transcript)
        if list_state["on"]:
            import re as _re
            toks = set(_re.findall(r"\w+", (payload.get("transcript") or "").lower()))
            done = bool(toks & END_WORDS)
            if not done and payload.get("product_id") and payload["status"] in ("OK", "OUT_OF_STOCK"):
                cart.add(payload["product_id"])
            if done:
                list_state["on"] = False
            r = payload.get("result") or {}
            broker.publish("list", {"heard": payload.get("transcript"), "status": payload["status"],
                                    "product": r.get("product"), "items": cart.items(), "done": done})
        else:
            broker.publish("result", payload)
        return payload

    @app.post("/find-product")
    async def find(request: Request):
        need_kiosk(request)
        try:
            body = await request.json()
            product_id = body["product_id"]
            if not isinstance(product_id, str):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            raise ApiError(422, "INVALID_BODY", 'Expected {"product_id": "P001", "language": "en"}')
        result = find_product(conn, product_id)
        if result is None:
            raise ApiError(404, "UNKNOWN_PRODUCT", f"Unknown product_id {product_id}")
        return {"request_id": _rid(), **result}

    @app.get("/kiosk/events")
    async def kiosk_events(request: Request):
        need_kiosk(request)
        return StreamingResponse(event_stream(broker), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    @app.get("/tts/{name}")
    async def tts(name: str, request: Request):
        need_kiosk(request)
        f = engine.CACHE / name
        if not re.fullmatch(r"[0-9a-f]{16}\.mp3", name) or not f.is_file():
            raise ApiError(404, "UNKNOWN_AUDIO", "No such audio file")
        return FileResponse(f, media_type="audio/mpeg")

    from app.cart import Cart
    cart = Cart(conn)
    END_WORDS = {"done", "mudinchu", "mudinjathu", "bas", "basa", "khatam", "முடிந்தது", "முடிஞ்சது", "बस", "खत्म"}
    list_state = {"on": False}

    @app.post("/list/start")
    async def list_start(request: Request):
        need_kiosk(request)
        cart.clear()
        list_state["on"] = True
        return {"list": True}

    async def _pid(request):
        try:
            pid = (await request.json())["product_id"]
            if not isinstance(pid, str):
                raise TypeError
            return pid
        except (ValueError, KeyError, TypeError):
            raise ApiError(422, "INVALID_BODY", 'Expected {"product_id": "P001"}')

    @app.get("/cart")
    async def cart_get(request: Request):
        need_kiosk(request)
        return {"items": cart.items()}

    @app.post("/cart/add")
    async def cart_add(request: Request):
        need_kiosk(request)
        if not cart.add(await _pid(request)):
            raise ApiError(404, "UNKNOWN_PRODUCT", "Unknown product_id")
        return {"items": cart.items()}

    @app.post("/cart/remove")
    async def cart_remove(request: Request):
        need_kiosk(request)
        cart.remove(await _pid(request))
        return {"items": cart.items()}

    @app.post("/cart/clear")
    async def cart_clear(request: Request):
        need_kiosk(request)
        cart.clear()
        return {"items": []}

    @app.get("/cart/route")
    async def cart_route(request: Request):
        need_kiosk(request)
        return cart.route()

    if os.environ.get("MRA_TTS_SYNC") == "1":
        from app.tts.sync import start_background
        start_background()
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "..", "kiosk"), html=True), name="kiosk")
    return app
