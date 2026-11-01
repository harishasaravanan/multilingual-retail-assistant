# Evaluation Report (interim)

All numbers are measured. Targets are goals only (SAD 13.3).

## 1. Product-match accuracy
| Set | Speakers | Result | Notes |
|---|---|---|---|
| Dev (80 clips) | 1 | 80/80 | Used to build aliases, prompt and matcher. Optimistic. One clip replaced to reach 80/80 (old one in results/accuracy/rejected_clips). |
| s3 (40 clips, run 15) | 1 | 33/40 (en 8/10, hi 9/10, ta_en 9/10, ta 6/10) | Dev-adjacent: 5 aliases and matcher fixes came from s3 misses. |
| s4 | 1 | pending | Clean held-out set, run once, no tuning. |

s3 runs: run11 26/40, run12 32/40 (echo guard, aliases), run13 29/40 (no Whisper prompt, rejected), run14 29/40, run15 33/40 (matcher coverage fix). Whisper small scored 19/40 on s3 and was rejected. With 10 clips per style, a swing of 1 to 3 clips is partly noise.

SAD targets: en 95%, hi 85%, ta 85%, ta_en 75%. Only hi and ta_en meet them on s3, with n=10 per style. en and ta miss.

Failure causes: Whisper echoing its vocabulary prompt on quiet clips (guarded), garbled Tamil decoding, short brand words ("Sprite"). One wrong-product match remains (P003_ta matched Oreo at 1.0). Wrong matches are worse than "please repeat".

## 2. WER (s3, Whisper medium)
en 33%, hi 74%, ta_en 69%, ta 90%. Only en is meaningful: the sheet writes brands in Latin script while STT emits Devanagari or Tamil script, so script mismatch counts as error. hi, ta and ta_en are judged by product accuracy.

## 3. Noise (s3, synthetic white noise)
| SNR | Correct |
|---|---|
| clean | 33/40 |
| 20 dB | 32/40 |
| 10 dB | 23/40 |
| 5 dB | 24/40 |
White noise only. Whisper hallucinates English on noisy Tamil clips. A real store-noise set is not recorded yet.

## 4. Latency (R9: p50 < 3 s, p95 < 5 s)
- Backend, clean s3 run, Whisper medium: 40 requests, p50 4.1 s, p95 5.25 s (STT + processing, after end of speech).
- Earlier mixed clean and noisy run: stt p50 4.17 s, p95 4.89 s (273 requests).
- PC (i7-14700), medium, 8 threads: STT median 2.96 s, p95 3.10 s. Small: median 1.29 s but accuracy 19/40.
- Result: R9 is not met with local Whisper medium on CPU, and VAD, network and TTS start add more. Deviation reported. Mitigation: streaming STT or a GPU.

## 5. Routing (R6)
10 destinations give distinct routes by aisle (results/routing/routing_10.txt).

## 6. Kiosk UI and spoken reply
States verified: tap-to-start, result, not found, please repeat, out of stock, error, offline with recovery. Tamil and Hindi replies reviewed by ear. Per project decision, price and stock are not shown or spoken; they stay in the data model and API.

## 7. Device (SiWx917, BRD2605A Rev A02)
- Done: board detected, build/flash chain works (LED blink), stock mic demo shows levels tracking speech.
- Pending: clean 16 kHz mono WAV from both mics (R1), HPF/AGC, VAD 20/20 and PTT (R2), Wi-Fi + HTTPS streaming (R3), LED from status, reconnect time, RAM/flash/CPU.
- Gap: Tier 1 is not complete until the board streams audio. Until then `send_wav.py` stands in for the device.

## 8. Open items
s4 held-out run, TLS on backend, real-noise test, device figures, demo video.
