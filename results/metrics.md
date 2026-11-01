# Metrics (measured)

## Accuracy (product match)
| Set | Result |
|---|---|
| Dev set (80 clips, run 10) | 80/80 |
| s3 held-out (40 clips, run 15) | 32/40: en 8/10, hi 9/10, ta_en 9/10, ta 6/10 |
SAD targets: en 95%, hi 85%, ta 85%, ta_en 75%. Met: hi, ta_en. Missed: en, ta. s3 was used for tuning, so it is dev-adjacent. Whisper small: 19/40, rejected.

## WER (s3, medium)
en 33%, hi 74%, ta_en 69%, ta 90%. Script mismatch inflates hi/ta/ta_en; only en is meaningful.

## Noise (s3, synthetic white noise)
| SNR | Correct |
|---|---|
| clean | 32/40 |
| 20 dB | 32/40 |
| 10 dB | 23/40 |
| 5 dB | 24/40 |

## Latency (R9: p50 < 3 s, p95 < 5 s) NOT MET
- Backend STT + processing: p50 4.1 s, p95 5.25 s (40 requests).
- PC i7-14700, medium, 8 threads: STT median 2.96 s, p95 3.10 s.
- Mitigation: streaming STT or GPU.

## Simulated network (PC loopback, mean of 3)
| Delay each way / loss | Upload | STT + response | Total |
|---|---|---|---|
| 0 ms / 0% | 0.0 s | 3.04 s | 3.04 s |
| 50 ms / 0% | 0.81 s | 3.09 s | 3.90 s |
| 100 ms / 2% | 1.61 s | 3.43 s | 5.05 s |
| 200 ms / 5% | 3.96 s | 5.01 s | 8.97 s |
Simulator opens a connection per chunk and uploads after the fact, so it overstates real cost. Board RTT and reconnect not measured.

## Board (SiWx917)
| Item | Result |
|---|---|
| VAD 20 utterances | run 1: 19/20, run 2: 17/20 (misses cut off at the 3 s window) |
| Push-to-talk | 8/8 detected |
| Flash | 224 KB of 2,040 KB (11%) |
| RAM (static) | 163 KB of 190 KB (86%) |
| CPU load | TODO (board) |
| Live capture to backend | TODO (board) |
| Reconnect after AP drop | TODO (board) |
| End-to-end latency | TODO (board) |

## Security (R3, R11)
TLS 1.3 and device-token tests 13/13. Simulator checks 8/8 (401 no/bad token, 404 unknown session, 410 closed session, 422 bad chunk).

## Routing (R6)
10 destinations give distinct routes (results/routing/routing_10.txt).

## UI and voice
States verified: tap-to-start, result, not found, please repeat, out of stock, error, offline with recovery. Tamil and Hindi replies reviewed by ear.

## Not measured
s4 set (optional), real store noise, board CPU/RTT/reconnect/end-to-end latency.
