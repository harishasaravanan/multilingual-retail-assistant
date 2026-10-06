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
        await edge_tts.Communicate(text, VOICES[lang]).save(str(f))
    return f
