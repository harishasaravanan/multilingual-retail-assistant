import numpy as np

_model = None
PROMPT = ("Dove shampoo, Dove conditioner, Amul butter, Amul milk, Amul cheese, "
          "Tata salt, Maggi noodles, Thums Up, sugar, Oreo biscuit.")

def _get():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)
    return _model

def transcribe(pcm: bytes) -> str:
    """16 kHz, 16-bit, mono little-endian PCM -> text."""
    if len(pcm) < 3200:  # under 0.1 s
        return ""
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    m = _get()
    segs, info = m.transcribe(audio, beam_size=1, vad_filter=True, initial_prompt=PROMPT)
    segs = list(segs)
    if info.language not in ("en", "ta", "hi"):  # e.g. Sinhala garbage on Tanglish
        segs, _ = m.transcribe(audio, beam_size=1, vad_filter=True, language="ta", initial_prompt=PROMPT)
        segs = list(segs)
    return " ".join(s.text for s in segs).strip()
