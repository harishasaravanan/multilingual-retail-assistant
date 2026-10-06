import asyncio, hashlib, pathlib, sys
import edge_tts

VOICES = {"en": "en-IN-NeerjaNeural", "ta": "ta-IN-PallaviNeural", "hi": "hi-IN-SwaraNeural"}
OUT = pathlib.Path(__file__).resolve().parents[1] / "tts_cache"

def key(lang, text):
    return hashlib.sha1(f"{lang}|{text}".encode()).hexdigest()[:16]

async def gen(lang, text):
    OUT.mkdir(exist_ok=True)
    f = OUT / f"{key(lang, text)}.mp3"
    if not f.exists():
        await edge_tts.Communicate(text, VOICES[lang]).save(str(f))
    return f

if __name__ == "__main__":
    print(asyncio.run(gen(sys.argv[1], sys.argv[2])))
