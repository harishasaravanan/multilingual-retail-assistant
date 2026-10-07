"""Pre-generate missing spoken replies. Run from backend/: python3 -m scripts.gen_all"""
import asyncio
from app.tts.sync import sync_missing

if __name__ == "__main__":
    asyncio.run(sync_missing())
