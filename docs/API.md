# API Specification

Source of truth: [SAD.md](SAD.md) §7.6 and §8. Version: 1.0 (Tier 1). Base URL: `https://<backend-host>`. All traffic over TLS.

## Conventions
- Device calls send `Authorization: Bearer <DEVICE_TOKEN>`.
- Audio: raw PCM, 16 kHz, 16-bit, mono, little-endian, about 200 ms per chunk (`Content-Type: application/octet-stream`).
- JSON responses use UTF-8. Prices are numbers with a separate ISO 4217 `currency`.
- Every response carries `request_id` for log correlation.

## Status values
| status | Meaning | Screen/voice state |
|---|---|---|
| OK | Product found and in stock | result |
| OUT_OF_STOCK | Found, stock = 0 | out-of-stock |
| NOT_FOUND | No product matched | not found |
| LOW_CONFIDENCE | Match below threshold | please repeat |
| ERROR | Backend or STT failure | error / offline |

## External endpoints (device)

### POST /voice-query/start
Starts an utterance session.
```
Response 200
{ "session_id": "s_8f3a", "request_id": "r_001" }
```

### POST /voice-query/{session_id}/chunk
Body: raw PCM chunk. Response `204 No Content`. Errors: `401` bad token, `404` unknown session, `410` session expired.

### POST /voice-query/{session_id}/end
Closes the session and returns the final result.
```
Response 200
{
  "request_id": "r_001",
  "status": "OK",
  "language": "ta-en",
  "reply_language": "ta",
  "product_id": "P001",
  "confidence": 0.93,
  "result": { ...same object as /find-product... },
  "tts_audio_url": "/tts/abc123.wav"
}
```
The device uses only `status` (LED feedback). The kiosk UI receives the same payload over a host-side push channel (SSE or WebSocket between backend and UI).

## Internal endpoint

### POST /find-product
Called by the orchestrator after matching; also used by tests.
```
Request
{ "product_id": "P001", "language": "ta-en" }

Response 200
{
  "product": "Dove Shampoo",
  "available": true,
  "stock": 12,
  "price": 249,
  "currency": "INR",
  "aisle": 7,
  "shelf": 3,
  "x": 18,
  "y": 42,
  "route": {
    "nodes": ["KIOSK", "A1", "A2", "A3", "A7"],
    "steps": ["Walk straight to A1", "..."]
  }
}
```
Errors: `404` unknown `product_id`, `422` invalid body.

## Other endpoints
| Endpoint | Tier | Notes |
|---|---|---|
| GET /health | 1 | `{ "status": "up" }` |
| /admin/* | 2 | Auth required; stock, aliases, map editing |

## Language policy
- `language` is the detected style (`en`, `ta`, `hi`, `ta-en` for Tanglish). It is advisory.
- `reply_language`: same as input for en/ta/hi; Tamil for Tanglish; English if confidence is low.
- Product resolution never depends on the language label.

## Data model (Tier 1)
| Field | Type | Rules |
|---|---|---|
| product_id | text | unique, e.g. P001 |
| name | text | display and spoken name |
| category | text | grouping |
| price | number | non-negative |
| currency | text | ISO 4217, INR for MVP |
| stock | integer | never negative |
| aisle, shelf | integer | physical location |
| x, y | number | map coordinates |
| node | text | must reference a valid map node |

Aliases table: `alias_id`, `product_id`, `alias`, `script` (latin, tamil, devanagari), `language` (en, ta, hi, ta-en).

## Consistency rule
Screen text and spoken reply are generated from the same `result` object, so price, currency and location always match.
