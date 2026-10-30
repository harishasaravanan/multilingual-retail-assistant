import os, sys, time, glob, wave, statistics, subprocess
os.environ["MRA_WHISPER_MODEL"] = "medium"
os.environ["MRA_WHISPER_THREADS"] = "8"
sys.path.insert(0, "backend")
import numpy as np
from app import stt_whisper as S
folder, n = sys.argv[1], int(sys.argv[2])
files = sorted(glob.glob(folder + "/*.wav"))
files = files[::max(1, len(files) // n)][:n]
def pcm(f):
    subprocess.run(["ffmpeg","-nostdin","-y","-loglevel","error","-i",f,"-ar","16000","-ac","1","-sample_fmt","s16","/tmp/_l.wav"], check=True)
    with wave.open("/tmp/_l.wav") as w:
        return w.readframes(w.getnframes())
KW = dict(beam_size=1, vad_filter=True, initial_prompt=S.PROMPT, condition_on_previous_text=False, no_speech_threshold=0.6)
fb = [0]
def b(d):
    if len(d) < 3200: return ""
    a = np.frombuffer(d, dtype=np.int16).astype(np.float32) / 32768.0
    m = S._get()
    segs, info = m.transcribe(a, language=None, **KW)
    segs = list(segs)
    if info.language not in ("en", "ta", "hi"):
        fb[0] += 1
        p = dict(info.all_language_probs or [])
        lang = max(("en", "ta", "hi"), key=lambda l: p.get(l, 0))
        segs, _ = m.transcribe(a, language=lang, **KW)
        segs = list(segs)
    return S._strip_echo(" ".join(s.text for s in segs).strip())
ds = [pcm(f) for f in files]
S.transcribe(ds[0]); b(ds[0]); fb[0] = 0
ta, tb, diff = [], [], []
for f, d in zip(files, ds):
    t = time.perf_counter(); x = S.transcribe(d); ta.append(time.perf_counter() - t)
    t = time.perf_counter(); y = b(d); tb.append(time.perf_counter() - t)
    if x != y: diff.append((os.path.basename(f), x[:50], y[:50]))
print(f"{folder}: A(current) median {statistics.median(ta):.2f}s | B(single pass) median {statistics.median(tb):.2f}s | differ {len(diff)}/{len(files)} | B fallbacks {fb[0]}")
for r in diff[:10]: print("  ", r)
