import re
import numpy as np

_model = None
PROMPT = ("Dove shampoo, Dove conditioner, Amul butter, Amul milk, Amul cheese, "
          "Tata salt, Maggi noodles, Thums Up, sugar, Oreo biscuit.")

def _get():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(__import__("os").environ.get("MRA_WHISPER_MODEL", "small"), device="cpu", compute_type="int8", cpu_threads=int(__import__("os").environ.get("MRA_WHISPER_THREADS", "8")))
    return _model

def transcribe(pcm: bytes) -> str:
    """16 kHz, 16-bit, mono little-endian PCM -> text."""
    if len(pcm) < 3200:  # under 0.1 s
        return ""
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    m = _get()
    _, _, probs = m.detect_language(audio)
    probs = dict(probs)
    lang = max(("en", "ta", "hi"), key=lambda l: probs.get(l, 0))
    segs, _ = m.transcribe(audio, beam_size=1, vad_filter=True, language=lang, initial_prompt=(None if __import__("os").environ.get("MRA_NO_PROMPT") else PROMPT), condition_on_previous_text=False, no_speech_threshold=0.6)
    segs = list(segs)
    return _strip_echo(" ".join(s.text for s in segs).strip())

_PH = [p.strip(" .").lower() for p in PROMPT.split(",")]
def _strip_echo(t):
    if sum(p in t.lower() for p in _PH) < 3:
        return t
    for p in _PH:
        t = re.sub(re.escape(p), "", t, flags=re.I)
    return re.sub(r"[\s,.]+", " ", t).strip(" ,.")
