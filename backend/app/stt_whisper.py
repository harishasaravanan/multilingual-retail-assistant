import numpy as np

_model = None

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
    segs, _ = _get().transcribe(audio, beam_size=1, vad_filter=True)
    return " ".join(s.text for s in segs).strip()
