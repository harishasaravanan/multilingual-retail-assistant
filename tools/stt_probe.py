import sys, subprocess, wave
import numpy as np
sys.path.insert(0, "/home/magiclab/harisha/mra-pc/backend")
from app import stt_whisper as S

def load(f):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f, "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", "/tmp/_p.wav"], check=True)
    with wave.open("/tmp/_p.wav") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

def db(x):
    return 20 * np.log10(max(float(x), 1e-9))

def run(m, a, lang, **over):
    kw = dict(beam_size=1, vad_filter=True, language=lang, initial_prompt=S.PROMPT, condition_on_previous_text=False, no_speech_threshold=0.6)
    kw.update(over)
    segs, _ = m.transcribe(a, **kw)
    return " ".join(s.text for s in list(segs)).strip()

m = S._get()
for f in sys.argv[1:]:
    a = load(f)
    pk = float(np.max(np.abs(a)))
    rms = float(np.sqrt(np.mean(a ** 2)))
    print("\n%s %.1fs peak %.1f rms %.1f dBFS" % (f.split("/")[-1], len(a) / 16000, db(pk), db(rms)))
    _, _, pr = m.detect_language(a)
    pr = dict(pr)
    lang = max(("en", "ta", "hi"), key=lambda l: pr.get(l, 0))
    n = a * (0.9 / pk) if pk > 0 else a
    P2 = S.PROMPT + " Vim dishwash liquid, Tide detergent."
    variants = [("current", a, {}), ("vad off", a, dict(vad_filter=False)), ("vad 0.3", a, dict(vad_parameters=dict(threshold=0.3))), ("no-speech off", a, dict(no_speech_threshold=None)), ("normalised", n, {}), ("prompt+2 names", a, dict(initial_prompt=P2))]
    for name, au, o in variants:
        print("  %-15s lang=%s %r" % (name, lang, run(m, au, lang, **o)))
