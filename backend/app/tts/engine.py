import hashlib, os, pathlib

VOICES = {"en": "en-IN-NeerjaNeural", "ta": "ta-IN-PallaviNeural", "hi": "hi-IN-SwaraNeural"}
CACHE = pathlib.Path(os.environ.get("MRA_TTS_DIR", pathlib.Path(__file__).resolve().parents[2] / "tts_cache"))

def key(lang, text):
    return hashlib.sha1(f"{lang}|{text}".encode()).hexdigest()[:16]

def path_for(lang, text):
    return CACHE / f"{key(lang, text)}.mp3"

def url_for(lang, text):
    """URL if the audio is already cached, else None. No network at request time."""
    return f"/tts/{key(lang, text)}.mp3" if path_for(lang, text).exists() else None

async def generate(lang, text):
    import edge_tts  # lazy: only the pre-generation script needs it
    CACHE.mkdir(parents=True, exist_ok=True)
    f = path_for(lang, text)
    if not f.exists():
        import threading
        tmp = f.with_name(f"{f.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            await edge_tts.Communicate(text, VOICES[lang]).save(str(tmp))
            os.replace(tmp, f)  # atomic: no half-written mp3 is ever served
        finally:
            if tmp.exists():
                tmp.unlink()
    return f

def url_or_generate(lang, text, timeout=8):
    """Cached URL, else (if MRA_TTS_ONMISS=1) generate now, else None."""
    u = url_for(lang, text)
    if u or os.environ.get("MRA_TTS_ONMISS") != "1":
        return u
    import asyncio, threading
    def run():
        try:
            asyncio.run(asyncio.wait_for(generate(lang, text), timeout))
        except Exception as e:
            print("tts on-miss FAILED", lang, text[:40], e, flush=True)
    t = threading.Thread(target=run)
    t.start()
    t.join(timeout + 1)
    return url_for(lang, text)
