# Multilingual AI-Powered Smart Retail Assistant

Voice-enabled retail kiosk. The Silicon Labs SiWx917-DK2605A captures audio and streams it securely to a backend that finds the product, checks stock and price, computes the aisle route, and answers on screen and by voice.

Full design: [docs/SAD.md](docs/SAD.md)

## How it works
Customer voice -> SiWx917 (mic, HPF/AGC, VAD, TLS) -> backend (STT, language ID, normalizer, matcher, DB, routing, TTS) -> kiosk UI + host speaker.

## Languages
| Input | Reply |
|---|---|
| English | English |
| Tamil | Tamil |
| Hindi | Hindi |
| Tanglish | Tamil (brand names in English) |

## Hardware
- SiWx917-DK2605A
- Kiosk host (laptop / mini-PC / tablet) with speaker

## Setup
1. `cp firmware/siwx917/config/wifi_config.example.h firmware/siwx917/config/wifi_config.h` and fill in values (git-ignored).
2. Create the DB: `sqlite3 retail.db < database/schema/schema.sql`, then load `database/sample_products.csv` and `database/seed/aliases.csv`.
3. Backend, firmware and kiosk run instructions: _to be added per phase_.

## Status
| Phase | State |
|---|---|
| 0 Architecture | in progress |
| 1-7 | not started |

## Results
Latency, accuracy and WER are published under `results/` after Phase 7. Targets in the SAD are goals; only measured numbers are reported.

## Roadmap
- Tier 1: MVP (voice capture, VAD/PTT, TLS streaming, 4 language styles, search, route, UI, TTS, metrics)
- Tier 2: polish (phonetic matching, confirmation, alternatives, BLE provisioning, admin, Docker, STT fallback)
- Tier 3+: multi-item routes, offers, QR handoff, wake word, signed OTA

## Team
_Add names._
