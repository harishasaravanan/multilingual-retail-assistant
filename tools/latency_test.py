import sys, time, wave, numpy as np
sys.path.insert(0, "/home/magiclab/mra-pc/backend")
from app import stt_whisper as S
def load(p):
    with wave.open(p) as w: return w.readframes(w.getnframes())
def single(pcm):
    a = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    m = S._get()
    kw = dict(beam_size=1, vad_filter=True, condition_on_previous_text=False, initial_prompt=S.PROMPT)
    segs, info = m.transcribe(a, language=None, **kw)
    segs = list(segs)
    if info.language not in ("en", "ta", "hi"):
        probs = dict(info.all_language_probs or [])
        lang = max(("en", "ta", "hi"), key=lambda l: probs.get(l, 0))
        segs, _ = m.transcribe(a, language=lang, **kw); segs = list(segs)
    return S._strip_echo(" ".join(s.text for s in segs).strip())
files = sys.argv[1:]
S.transcribe(load(files[0]))  # warm-up
ta = tb = 0.0; same = 0
for f in files:
    p = load(f)
    t = time.perf_counter(); a = S.transcribe(p); ta += time.perf_counter() - t
    t = time.perf_counter(); b = single(p); tb += time.perf_counter() - t
    same += (a.strip().lower() == b.strip().lower())
    print(f"{f.split('/')[-1]:30s} two-pass={a!r}  single={b!r}")
n = len(files)
print(f"\navg two-pass {ta/n:.2f}s  single-pass {tb/n:.2f}s  saved {(ta-tb)/n:.2f}s  identical {same}/{n}")
