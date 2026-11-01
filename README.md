# Multilingual AI-Powered Smart Retail Assistant (SiWx917-DK2605A)

Voice kiosk: a customer asks for a product in English, Hindi, Tamil or Tanglish. The SiWx917 captures and streams audio over HTTPS/TLS. The backend runs Whisper STT, matching, DB lookup and routing. The kiosk shows the result and route and speaks the answer.

Spec: SAD v2.3 (docs/SAD.md), API: docs/API.md. Per SAD v2.3, price is not shown or spoken; stock is reported as available / out of stock.

Team: (add names)

## Layout
- firmware/siwx917/mra_wifi2: mic capture, HPF/AGC, VAD, PTT (BTN0), LED, TLS upload
- backend/: FastAPI, Whisper STT, matcher, routing, TTS
- kiosk/: web UI, served by the backend at /
- tests/, scripts/, tools/, results/, docs/

## Run the backend
```
cd backend
export MRA_DEVICE_TOKEN=<token> MRA_KIOSK_TOKEN=dev-kiosk MRA_STT=whisper MRA_WHISPER_MODEL=medium MRA_WHISPER_THREADS=8
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```
Open the kiosk at http://127.0.0.1:8000/. The database is built at startup.

## Test without the board
```
export MRA_DEVICE_TOKEN=<token>
python3 tools/device_sim.py r11          # security checks (401/404/410/422)
python3 tools/device_sim.py <clip.wav>   # replay a 16 kHz mono WAV
```

## Firmware
Copy wifi_config.h.example to wifi_config.h and set Wi-Fi, host and token. Never commit it. Build in Simplicity Studio.

## Status
Done: Phases 0 to 6, firmware capture/VAD/PTT/TLS upload, backend, kiosk, tags sad-M0 to sad-M6.
Not yet measured (need the board): live capture to backend, reconnect time, CPU load, end-to-end latency, real demo (sad-M7).
Not done: Tier 2 (sad-M8).

## Known deviations
- R9 not met: p50 about 4.1 s, p95 about 5.25 s (target 3 s / 5 s). Cause: local Whisper medium on CPU.
- Accuracy below SAD targets for en and ta on the s3 held-out set (n=10 per style).
- No real store-noise test; noise tested with synthetic white noise.

Results: results/metrics.md, docs/evaluation_report.md
