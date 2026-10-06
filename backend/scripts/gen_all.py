"""Pre-generate every spoken reply. Run from backend/: python3 -m scripts.gen_all"""
import asyncio
from app.database.db import build_db
from app.service import find_product
from app.tts.engine import generate
from app.tts.replies import build_reply, spoken_language

LANGS = ("en", "ta", "hi")

def product_ids(conn):
    ids = set()
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
        if "product_id" in cols:
            ids |= {r[0] for r in conn.execute(f"SELECT product_id FROM {t}")}
    return sorted(ids)

def items(conn):
    todo = set()
    for pid in product_ids(conn):
        result = find_product(conn, pid)
        if result is None:
            continue
        status = "OK" if result["available"] else "OUT_OF_STOCK"
        for lang in LANGS:
            todo.add((spoken_language(status, lang), build_reply(status, lang, result)))
    for status in ("NOT_FOUND", "LOW_CONFIDENCE", "ERROR"):
        for lang in LANGS:
            todo.add((spoken_language(status, lang), build_reply(status, lang)))
    return sorted(todo)

async def main():
    todo, failed = items(build_db()), 0
    for lang, text in todo:
        try:
            await asyncio.wait_for(generate(lang, text), 30)
            print('ok', lang, text[:40], flush=True)
        except Exception as e:
            failed += 1
            print("FAILED", lang, text[:40], e)
    print(f"{len(todo) - failed}/{len(todo)} audio files ready")

asyncio.run(main())
