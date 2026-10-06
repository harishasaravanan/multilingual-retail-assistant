# System Architecture Document
## Multilingual AI-Powered Smart Retail Assistant using SiWx917-DK2605A

| Field | Value |
|---|---|
| Document ID | MRA-SW917-SAD-002 |
| Version | 2.2 (supersedes 2.1) |
| Status | Proposed / Implementation Ready |
| Target Platform | SiWx917-DK2605A (BRD2605A) |
| Connectivity | Wi-Fi 6-capable wireless connectivity with secure IP transport; BLE |
| Languages | English, Tamil, Hindi, Tanglish |
| Output | Kiosk screen + spoken reply through the kiosk host speaker |

### Changes from v2.1
- Added `node` to the data model; route example made consistent with §9.
- Tier 1 push channel frozen as SSE; API details moved to `docs/API.md` v1.1.

### Changes from v2.0
- Scope tiers rewritten: Tier 1 is the mandatory MVP; Tier 2 is polish. No contradictions between sections.
- Local STT fallback, confirmation flow, alternatives, admin dashboard, analytics, Docker, BLE provisioning and advanced phonetic matching moved to Tier 2. Basic alias + fuzzy matching stays in Tier 1.
- Spoken reply through a speaker is explicit, and the spoken reply includes price details (price is not screen-only).
- Wi-Fi wording corrected (no special "Wi-Fi 6 streaming protocol" implied).
- Hardware risk added: microphone function and board revision check.
- Latency budget wording corrected (stage sum vs acceptance target).
- Dataflow now shows audio to `/voice-query`, then normalizer, matcher, product ID, then lookup. `/find-product` is internal.
- Tier 1 transport frozen: HTTPS chunked upload over TLS.
- Language policy defined: Tanglish is an input style; replies for Tanglish input are in Tamil. Language ID is advisory.
- `currency` added to the data model and API.
- RAM wording: whole-utterance buffering is prohibited by architectural choice (memory and latency).
- Kiosk host defined (UI + speaker host).
- Added §11.1 Repository and Version Control.

---

## 1. Executive Summary

A voice-enabled retail kiosk. A customer presses a button (or speaks, with VAD) and asks for a product in English, Tamil, Hindi or Tanglish. The SiWx917 captures audio, detects speech on-device, and streams it over secure IP (Wi-Fi) to a backend. The backend performs STT, language ID, normalization, product matching, database lookup and route calculation. The kiosk shows the result and highlighted route on screen **and speaks the answer, including price, through the kiosk host speaker**.

Heavy AI stays on the backend for the MVP. The SiWx917 is a real embedded component: audio capture, pre-processing, VAD, secure streaming, status feedback.

---

## 2. Scope and Requirements

### 2.1 Tier 1 (Mandatory MVP)
- SiWx917 bring-up, digital mic capture, HPF/AGC.
- VAD and push-to-talk.
- Wi-Fi connection (credentials from build config) and TLS audio streaming.
- English, Tamil, Hindi and Tanglish product requests on a controlled catalog.
- Streaming (chunked) STT with language ID.
- Normalization, alias table (multi-script), basic fuzzy matching.
- Database: product, price, stock, aisle, shelf, coordinates.
- Route calculation from fixed kiosk on a graph; step-by-step route text.
- Kiosk UI: product, availability, stock, price, aisle/shelf, highlighted route.
- Basic TTS reply through the kiosk host speaker, including price.
- Basic error handling: unknown, out-of-stock, low-confidence (ask to repeat), network failure.
- Status feedback: RGB LED states.
- Structured logging and measured metrics.

### 2.2 Tier 2 (Polished)
- Advanced fuzzy/phonetic matching and disambiguation (Dove vs Dove Men).
- Confirmation flow ("Did you mean X?").
- Alternatives when out of stock.
- BLE Wi-Fi provisioning.
- Admin dashboard (stock, aliases, map editor) and analytics.
- Local STT fallback (e.g. Whisper).
- Docker deployment, health checks, rate limiting.
- Noise suppression on device, board-side speaker playback via I2S amplifier.
- Weighted graph with one-way/blocked edges, ETA.
- Accessibility modes (large text, voice-only).

### 2.3 Tier 3 and Beyond (Future)
- Multi-item shopping list with optimized route, category queries, offers/discounts.
- QR phone handoff, wake word, signed OTA, more languages.
- Indoor positioning, personalization, edge STT, multi-store sync.

### 2.4 Out of Scope
- Full conversational shopping assistant.
- Preference/budget-based recommendation.
- Production-scale multi-store inventory synchronization.

### 2.5 Requirements

| ID | Tier | Requirement | Acceptance |
|---|---|---|---|
| R1 | 1 | Board audio capture works | Saved WAV at 16 kHz/16-bit mono is clean, repeatable |
| R2 | 1 | On-device VAD / push-to-talk | Utterance start/end detected on board; silence not streamed |
| R3 | 1 | Reliable secure transport | Audio and JSON exchanged over TLS; auto-reconnect works |
| R4 | 1 | Structured query | Requests resolve to ACTION + product ID |
| R5 | 1 | Database-driven results | No hard-coded answers in final demo |
| R6 | 1 | Route from map data | Changing destination changes route |
| R7 | 1 | Multilingual support | English, Tamil, Hindi, Tanglish test sets measured |
| R8 | 1 | Failure handling | Unknown, out-of-stock, low-confidence, network-down have clear screen and voice states |
| R9 | 1 | Latency | p50 < 3 s and p95 < 5 s from end-of-user-speech to first visible result and start of spoken response |
| R10 | 1 | Measured results | All metrics from real tests, test set published |
| R11 | 1 | Security documented and implemented | TLS, device authentication, least-privilege API |
| R12 | 1 | Spoken reply | Reply played through the kiosk host speaker in the selected reply language according to the language policy (§7.4); includes product, availability, location and price |
| R13 | 2 | BLE provisioning | Wi-Fi credentials set from phone without reflashing |

---

## 3. Problem Statement and Approach

Large stores make product discovery slow, and many customers prefer speaking in their own language. The kiosk converts a spoken request into a product location, route and spoken answer.

**Why embedded + backend:** the SiWx917 handles audio capture, pre-processing, VAD, wireless and device security. Speech, language, DB and routing run on a backend, which is realistic and easier to debug.

**Transport note:** the kit provides Wi-Fi 6-capable wireless connectivity (802.11ax, 2.4 GHz) with BLE. The application layer is ordinary secure IP transport. **Tier 1 transport is frozen: HTTPS chunked upload over TLS.** WebSocket and MQTT are not used between the device and backend in Tier 1. Do not claim Wi-Fi 6-specific throughput benefits.

---

## 4. System Architecture

**Kiosk host:** the laptop, mini-PC or tablet is the UI and speaker host (it runs the kiosk screen and plays the TTS audio). The SiWx917 is the embedded audio-capture and wireless device only.

```
            CUSTOMER
               | voice (button / VAD)
               v
     +-------------------------+
     |        SiWx917          |
     | mic -> HPF/AGC -> VAD   |
     | chunking, TLS, Wi-Fi    |
     | RGB LED, BTN0 (PTT)     |
     +-----------+-------------+
                 | HTTPS/TLS: audio chunks -> /voice-query
                 v
     +-------------------------------------------+
     |  Backend orchestrator                     |
     |  STT -> language ID -> normalizer         |
     |  -> product matcher -> product ID         |
     |  -> lookup (DB) -> routing -> result      |
     +----+--------------+--------------+--------+
          v              v              v
     +---------+   +-----------+   +---------+
     | Retail  |   | Routing   |   |  TTS    |
     | DB      |   | engine    |   | service |
     +---------+   +-----------+   +----+----+
                                        |
                  result JSON + audio   v
     +-------------------------------------------+
     | Kiosk UI (screen) + Speaker (spoken reply) |
     +-------------------------------------------+
```

### 4.1 Layers

| Layer | Components | Responsibility |
|---|---|---|
| Device | SiWx917 + mics + button + LED | Capture, pre-process, VAD, stream, status |
| Transport | Wi-Fi + TLS | Secure streaming and request/response |
| AI/Language | STT, language ID, normalizer | Voice to normalized text |
| Application | Matcher, orchestrator API | Product resolution, business logic |
| Data | Retail DB | Products, aliases, price, stock, locations |
| Navigation | Map + router | Path and step text |
| Presentation | Kiosk UI, TTS, speaker | Visual and spoken answer |
| Admin (Tier 2) | Dashboard, analytics | Stock, aliases, map, metrics |

### 4.2 Design Principles
- Layers are independent; the UI never touches the DB directly.
- The device only streams audio and receives status; it does not know about products.
- Every stage logs timestamps for latency analysis.
- Fail visibly and audibly: every error has a screen state and a spoken message.

### 4.3 Speaker Output
- **Tier 1:** the backend generates TTS audio; the kiosk host (laptop, mini-PC or tablet running the UI) plays it through its speaker. The board is not required to play audio.
- **Tier 2:** stream TTS audio back to the SiWx917 and play via an external I2S DAC/amplifier and speaker. This needs extra hardware and RAM for playback buffering, so treat it as an upgrade.
- The kit has no onboard speaker.

---

## 5. End-to-End Dataflow

The device does not know the product ID. It sends only audio. The backend resolves the product ID.

```
User: "Dove shampoo enga irukku?"
        |
        v
SiWx917: mic -> HPF/AGC -> VAD -> chunked audio over HTTPS/TLS -> /voice-query
        |
        v
STT: "Dove shampoo enga irukku?"
        |
        v
Language ID: Tanglish
        |
        v
Normalizer: intent=FIND, query="Dove shampoo"
        |
        v
Product matcher (aliases + fuzzy): Dove Shampoo -> P001  (confidence 0.93)
        |
        v
Internal lookup (/find-product, product_id=P001)
        |
        v
Database: P001 -> stock 12, price 249 INR, aisle 7, shelf 3, (x,y)
        |
        v
Router: KIOSK -> A1 -> A2 -> A3 -> A4 -> A5 -> A7  (+ step text)
        |
        v
Result JSON -> Kiosk UI (screen)  +  TTS -> Speaker
```

### 5.1 Normalization Examples
```
English:  "Where is Dove shampoo?"
Tamil:    "Dove shampoo எங்கே இருக்கு?"
Tanglish: "Dove shampoo enga irukku?"
Hindi:    "Dove shampoo कहाँ मिलेगा?"
STT may emit native-script brand names (e.g. "டவ் ஷாம்பு").
All -> intent=FIND, product_id=P001
```

### 5.2 Latency Budget (end-of-user-speech to first visible result and start of spoken response)

| Stage | Budget |
|---|---|
| VAD end-of-speech detection | 0.3 s |
| Final audio chunk + network | 0.3 s |
| STT finalization (streaming) | 1.0 s |
| Matching + DB + routing | 0.3 s |
| UI render + TTS start | 0.5 s |
| **Expected stage sum** | **about 2.4 s** |
| **Acceptance target** | **p50 under 3 s, p95 under 5 s** |

The 0.6 s margin covers real-world variance. Log every stage to confirm.

---

## 6. Hardware/Software Task Allocation

| Subsystem | Responsibility |
|---|---|
| SiWx917 firmware | Boot, audio capture, HPF/AGC, VAD, push-to-talk (BTN0), chunk streaming, TLS, Wi-Fi connect, RGB LED states, watchdog, reconnect, heartbeat. Tier 2: BLE provisioning, noise suppression, speaker playback |
| Speech service | Streaming STT, language ID |
| Normalizer + matcher | Intent and product text extraction, alias lookup, fuzzy match, confidence |
| Backend API | Orchestration, auth, validation |
| Database | Products, aliases, price, stock, map data |
| Routing engine | Path and step text |
| TTS service | Spoken reply per language |
| Kiosk UI + speaker | Screen result and audio playback |

---

## 7. Subsystem Specifications

### 7.1 Embedded Audio and Firmware
- Format: 16 kHz, 16-bit, mono (about 32 KB/s). Whole-utterance buffering is prohibited by architectural choice, to control memory use and latency; audio is always streamed from a ring buffer.
- Use a ring buffer and send frames of 20 to 100 ms.
- Pre-processing: high-pass filter, AGC (Tier 1); noise suppression (Tier 2).
- VAD: energy/zero-crossing based; BTN0 push-to-talk is the primary demo path and fallback.
- RGB LED states: idle, listening, processing, success, error, offline.
- Reliability: watchdog, Wi-Fi auto-reconnect with backoff, status heartbeat.
- Report RAM, flash and CPU usage.

### 7.2 Wi-Fi and Transport
- Station mode; credentials from build config in Tier 1 (BLE provisioning in Tier 2).
- TLS with device token or certificate.
- Application protocol frozen for Tier 1: HTTPS chunked upload. Each utterance is a session; the device POSTs about 200 ms audio chunks and the backend feeds them to streaming STT.
- Measure RTT, throughput, packet loss, reconnect time.

### 7.3 BLE (Tier 2)
- Wi-Fi provisioning and maintenance only, with authenticated pairing.
- Credentials never logged.

### 7.4 Speech and Language
- Streaming or chunked STT; language ID per utterance.
- Language ID is advisory: it selects the STT hint and the reply voice only. It need not be perfect on mixed-language or Tanglish speech. Product resolution runs on the normalized transcript and alias table, so a wrong language label must not change the matched product.
- Tanglish is an input style (Tamil with English words, spoken or romanized). Reply language for Tanglish input is Tamil: spoken and on-screen text in Tamil, with brand and product names kept in English. English, Hindi and Tamil inputs get replies in the same language. If language confidence is low, reply in English.
- Test order: English, Hindi, Tamil, then Tanglish.
- Local STT fallback is Tier 2. Tier 1 relies on one solid cloud/backend STT path.

### 7.5 Normalization and Matching
- Normalizer extracts intent and product phrase from the transcript.
- Tier 1: controlled vocabulary, aliases in English, Tamil script, Devanagari and Roman transliteration, plus basic fuzzy (edit distance) matching.
- Confidence handling in Tier 1: high confidence proceeds; low confidence gives "please repeat" on screen and voice.
- Tier 2: phonetic matching, "Did you mean X?" confirmation, multi-candidate disambiguation.

### 7.6 Backend API

External (device and kiosk):
```
POST /voice-query/start              (device auth) -> { "session_id": "..." }
POST /voice-query/{session_id}/chunk (raw 16 kHz/16-bit mono PCM, about 200 ms)
POST /voice-query/{session_id}/end   (returns the response below)
Response
{
  "status": "OK",
  "language": "ta-en",
  "reply_language": "ta",
  "product_id": "P001", "confidence": 0.93,
  "result": { ...see below... },
  "tts_audio_url": "/tts/abc123.wav"
}
```

The kiosk UI receives the same result from the backend over a host-side push channel. Tier 1 uses SSE (`GET /kiosk/events`); the full contract, error body, non-OK responses and session rules are in `docs/API.md` (v1.1), which is the source of truth for message shapes. The SiWx917 only uses `status` for LED feedback.

Internal (called by orchestrator after matching; also used by UI tests):
```
POST /find-product
{ "product_id": "P001", "language": "ta-en" }

Response
{
  "product": "Dove Shampoo", "available": true, "stock": 12,
  "price": 249, "currency": "INR", "aisle": 7, "shelf": 3, "x": 18, "y": 42,
  "node": "A7",
  "route": { "nodes": ["KIOSK","A1","A2","A3","A4","A5","A7"],
             "steps": ["Walk straight to A1", "..."] }
}
```

Other endpoints: `/health`; `/admin/*` (Tier 2, auth required).

### 7.7 Kiosk UI, TTS and Speaker
- Screen shows: product, availability, stock, **price**, aisle/shelf, highlighted route, step-by-step text.
- Spoken reply in the selected reply language (§7.4) includes: product name, availability, aisle and shelf, **price**, and a pointer to the route on screen.
  Example: "Dove Shampoo is available in aisle 7, shelf 3. Price is 249 rupees. Follow the route on the screen."
- Price is therefore both displayed and spoken. Amount and currency come from the same result object (249 INR is shown as ₹249 and spoken as "249 rupees" in the reply language).
- Error voices: out-of-stock ("currently unavailable"), not found, please repeat, network unavailable.
- States: listening, processing, result, out-of-stock, not found, please repeat, offline.
- Tier 2: confirmation screen, alternatives, large text mode, voice-only mode.

---

## 8. Retail Data Model

| Field | Example | Purpose |
|---|---|---|
| product_id | P001 | Unique ID |
| name | Dove Shampoo | Display and spoken name |
| aliases | table: alias, script, language | Recognition variants |
| category | Personal Care | Grouping |
| price | 249 | Shown on screen and spoken |
| currency | INR | Display symbol and spoken unit |
| stock | 12 | Quantity |
| aisle / shelf | 7 / 3 | Physical location |
| x, y | 18, 42 | Map coordinates |
| node | A7 | Map node the product sits on; must exist in the map |
| alternatives (Tier 2) | P002, P003 | Out-of-stock suggestions |

Rules:
- Unique product IDs; stock never negative; price non-negative; currency is an ISO 4217 code (INR for the MVP).
- Locations reference valid map nodes.
- Inventory state separate from static map data.
- Final UI and TTS use live API/DB results only.
- Tier 1: seed the DB with a script. Admin editing is Tier 2.

---

## 9. Store Map and Routing

- Fixed kiosk start for MVP.
- Graph: nodes are intersections and shelf points; edges are walkable links.
- Tier 1: BFS or Dijkstra on a small map; node list plus step text.
- Tier 2: weighted edges, one-way aisles, blocked edges, ETA, map editor.

```
KIOSK -> A1 -> A2 -> A3 -> A4 -> A5 -> A7/S3
```

---

## 10. Security Architecture

- Device authenticates with token or certificate; TLS on all traffic.
- Wi-Fi credentials stored in device config, not in logs.
- API: authentication and input validation (Tier 1); rate limiting (Tier 2).
- DB credentials never reach the kiosk or UI.
- Logs avoid personal data; audio is not retained by default (opt-in for testing only).
- Signed OTA and secure boot: Tier 3 (document if not implemented).

---

## 11. Toolflow

| Workstream | Tools | Output |
|---|---|---|
| Embedded | SiWx917 SDK / Simplicity Studio | Firmware |
| Backend | Python (FastAPI) or Node.js | API |
| Speech | Cloud STT (single path) | Transcript, language |
| Matching | rapidfuzz or similar | Product ID, confidence |
| Database | SQLite or PostgreSQL | Retail data |
| Routing | NetworkX or custom | Path |
| TTS | Cloud/local TTS supporting en, ta, hi | Spoken reply audio |
| UI | Web (React/HTML) | Kiosk screen + audio playback |
| Testing | Scripts, recorded test set | Metrics |
| Tier 2 | Docker, Whisper fallback | Deployment, resilience |

### 11.1 Repository and Version Control

One GitHub repository holds firmware, backend, kiosk UI, database, tests, docs and results. Run instructions live in the repository README, not in this SAD.

```
multilingual-retail-assistant/
├── README.md, LICENSE, .gitignore
├── docs/         SAD.md, architecture diagrams, API.md, evaluation report
├── firmware/
│   └── siwx917/  src/ (mic capture, HPF/AGC, VAD, streaming), include/, config/
├── backend/
│   ├── app/      api/, speech/, language/, matching/, database/, routing/, tts/
│   └── tests/
├── kiosk/        UI + host-speaker playback
├── database/     schema/, seed/, sample_products.csv
├── tests/        audio/, language/, matching/, routing/, integration/, test_dataset/
├── scripts/      setup/, evaluation/
├── deployment/   docker/, configs/   (Tier 2)
└── results/      latency/, accuracy/, wer/, demo/
```

Repository rules:
1. Board-specific code stays under `firmware/`; backend AI, API, DB and routing under `backend/`; UI and host-speaker integration under `kiosk/`.
2. Test datasets and evaluation scripts stay under `tests/`; architecture and API docs under `docs/`.
3. Secrets, Wi-Fi credentials, API keys and certificates are never committed. Commit an example config file only; keep the real one git-ignored.
4. Test audio is committed only with the speaker's consent.
5. Tier 1 work is tagged separately from Tier 2 work.
6. Each milestone (M0 to M8) gets a Git tag or release.

---

## 12. Phase-Wise Plan

| Phase | Focus | Time | Gate (must pass to proceed) |
|---|---|---|---|
| 0 | Architecture, API, schema, catalog | 2 days | API and schema frozen; 50-product catalog drafted; repository skeleton created |
| 1 | Board bring-up, mic check, audio, VAD | 4-5 days | Board revision and both mics verified; saved WAV clean; VAD detects 20/20 utterances; silence not sent |
| 2 | Wi-Fi, TLS, audio streaming | 4-5 days | Audio streams to backend and playback matches; reconnect works after AP drop |
| 3 | STT, language ID, normalizer, matcher | 8-10 days | English set met; Hindi, Tamil, Tanglish measured; matcher resolves aliases across scripts |
| 4 | DB + backend API | 3-4 days | `/voice-query/start`, `/chunk`, `/end` and `/find-product` return correct data for all catalog items |
| 5 | Map + routing | 3-5 days | Route correct for 10 test destinations |
| 6 | UI + TTS + speaker | 4-5 days | All UI states reachable; spoken reply (with price) plays in 3 languages |
| 7 | Integration, evaluation | 7-10 days | Full workflow repeats; metrics table complete; noise and network tests done |
| 8 | Tier 2 items (as time allows) | variable | Each Tier 2 feature has its own pass test; BLE provisioning, admin, fallback STT, etc. |

Record test logs and results as artifacts at every gate. Do not proceed if the gate fails.

---

## 13. Verification, Risks, Debugging

### 13.1 Failure Modes and Risks

| Failure / risk | Likely cause | Diagnostic | Mitigation |
|---|---|---|---|
| **Microphone hardware / board revision** | Board revision or hardware fault; digital mic not working or degraded | Phase 1 mic test on both ICS-43434 mics; record WAV; check board revision label and Silicon Labs errata/release notes | Verify in Phase 1 before continuing; if mics fail or are degraded, try the other mic, check errata, request exchange |
| No/garbled audio | Interface or format mismatch | Dump WAV on-board | Freeze audio format first |
| VAD cuts speech | Threshold, noise | Log VAD events | Hangover time; push-to-talk fallback |
| RAM exhaustion | Large buffers | Memory profiling | Frame streaming, ring buffer |
| Wi-Fi up, API fails | TLS, auth, address | Send simple JSON | Validate transport alone |
| STT errors | Noise, accent, code-mixing | Test recordings | Controlled vocabulary, noise control |
| Wrong product | Script/transliteration gap | Print normalized query | Expand aliases, fuzzy match |
| Wrong stock or price | DB issue | Direct query | Controlled test inventory |
| Wrong route | Graph error | Print path nodes | Validate graph connectivity |
| No sound / wrong language TTS | Speaker, TTS voice | Play test clip per language | Verify output device and TTS voices early |
| Spoken price differs from screen | Separate data paths | Compare TTS text with JSON | Generate both from the same result object |
| Latency over budget | One slow stage | Per-stage timestamps | Streaming STT, caching |
| Stale UI | State/cache bug | Compare API response | Refresh per request |

### 13.2 Debugging Order
1. Board boot and firmware.
2. Microphone function and audio capture without AI (WAV check).
3. VAD behavior.
4. Wi-Fi/TLS with a simple message.
5. Backend API independently.
6. STT on prerecorded audio.
7. Normalizer and matcher on text only.
8. DB lookup.
9. Routing with manual destination.
10. TTS and speaker output.
11. UI connection.
12. Full voice-to-screen-and-speech tests.

### 13.3 Evaluation Plan (target metrics)

| Item | Method | Target |
|---|---|---|
| Test set | 50+ products x 4 language styles x 5+ speakers | Published with results |
| Product-match accuracy | Correct product ID rate | English 95%, Hindi 85%, Tamil 85%, Tanglish 75% (report actuals) |
| WER | Per language | Reported |
| Latency | Per stage, p50/p95 | Stage sum about 2.4 s; p50 under 3 s, p95 under 5 s |
| Noise | Quiet, store-like, loud | Accuracy drop per level |
| Network | Weak signal, drop, reconnect | Recovery time |
| Device resources | RAM, flash, CPU | Reported |
| Spoken reply | Correct language, content includes price, matches screen | 100% match on test set |
| Failure cases | Unknown, out-of-stock, low-confidence, offline | All handled, screen and voice |
| Usability (optional) | 10 users, SUS; kiosk vs manual search time | Reported |

Targets are goals, not promises; always report measured values.

---

## 14. Milestones

| Milestone | Pass condition |
|---|---|
| M0 | Architecture, API, schema, catalog frozen |
| M1 | Mics verified; board captures clean audio; VAD works |
| M2 | Secure streaming to backend; auto-reconnect |
| M3 | All four language styles resolve to product IDs; measured |
| M4 | DB-driven price, stock, location |
| M5 | Correct routes and step text |
| M6 | UI and spoken reply (with price) complete with all states |
| M7 | Full workflow repeats; metrics, noise and network tests complete |
| M8 | Tier 2 features (optional, each tested) |

---

## 15. Definition of Done

- Customer presses the button or speaks and the board captures the request.
- Audio streams securely to the backend.
- Backend identifies the product with a confidence score.
- Database provides stock, price and location.
- Route and step text are generated from the fixed kiosk.
- Route shows on the map; price, stock and location are on screen.
- The answer, including price, is spoken through a speaker.
- English, Tamil, Hindi and Tanglish are demonstrated.
- Out-of-stock, unknown, low-confidence and network failures are handled on screen and by voice.
- Latency, accuracy, noise and network results are measured and reported.
- Device RAM/flash/CPU figures reported.
- No core result is hard-coded in the final demo.
- Recorded fallback demo video exists.

---

## Appendix A: Scope Tiers (summary)

| Tier | Features | Status |
|---|---|---|
| 1 MVP | Voice capture, VAD/PTT, Wi-Fi/TLS streaming, 4 language styles, product search, DB, stock/price/location, route, UI, basic TTS via kiosk host speaker (price included), basic error handling, metrics | Mandatory |
| 2 Polished | Advanced fuzzy/phonetic matching, confirmation flow, alternatives, BLE provisioning, admin dashboard, analytics, local STT fallback, Docker, noise suppression, board-side speaker, weighted routing, ETA, accessibility | Recommended |
| 3 Advanced | Multi-item routes, category queries, offers/discounts, QR handoff, wake word, signed OTA, more languages | Future |
| 4 Research | Indoor positioning, personalization, edge STT, multi-store sync | Future |

## Appendix B: Example Requests and Responses

| Style | Request | Normalized |
|---|---|---|
| English | Where is Dove shampoo? | FIND -> P001 |
| Tamil | Dove shampoo எங்கே இருக்கு? | FIND -> P001 |
| Hindi | Dove shampoo कहाँ मिलेगा? | FIND -> P001 |
| Tanglish | Dove shampoo enga irukku? | FIND -> P001 |

```
Found:        Screen: product, stock, price, aisle/shelf, route.
              Voice: "Dove Shampoo is in aisle 7, shelf 3. Price is 249 rupees."
Out-of-stock: "Dove Shampoo is currently unavailable."
Unknown:      "I could not find that product in this store."
Low-conf:     "Sorry, please say that again."
Offline:      "Network unavailable. Please try again."
```

## Appendix C: Glossary

| Term | Definition |
|---|---|
| SiWx917 | Silicon Labs wireless MCU used as the kiosk embedded platform |
| STT / TTS | Speech-to-text / text-to-speech |
| VAD | Voice activity detection |
| PTT | Push-to-talk |
| AGC | Automatic gain control |
| HPF | High-pass filter |
| WER | Word error rate |
| Tanglish | Mixed or transliterated Tamil-English |
| BLE | Bluetooth Low Energy |
| OTA | Over-the-air firmware update |
| SUS | System Usability Scale |
| p50 / p95 | Median / 95th percentile latency |

## Architecture Decision Summary

The SiWx917 serves as an embedded voice front-end (capture, pre-processing, VAD, secure streaming, status), while speech intelligence, matching, retail data, routing and TTS stay on the backend. The device sends only audio; the backend resolves the product ID. Answers are shown on screen and spoken through a speaker, with price in both. Tier 1 is a lean, reliable core; Tier 2 features are added only after Tier 1 passes its gates.
