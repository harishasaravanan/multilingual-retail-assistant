"""Advisory language/style detection and the reply-language policy (API.md).

The label only picks the reply voice. It never changes which product matches.
"""
from app.language.normalizer import clean

_TAMIL_LATIN = set(clean("enga enge engey engae ange irukku iruku irukkum irukka irukkuma "
                         "kidaikkum kidaikum kidaikuma venum vendum venumnu enakku sollunga").split())
_HINDI_LATIN = set(clean("kahan kahaan kaha milega milegi milta hai hain mujhe chahiye batao "
                         "bataiye dikhao kya kidhar").split())


def detect_language(text):
    """Return en, ta, hi or ta-en (Tanglish)."""
    if any("\u0900" <= ch <= "\u097f" for ch in text):
        return "hi"
    if any("\u0b80" <= ch <= "\u0bff" for ch in text):
        return "ta"
    words = set(clean(text).split())
    if words & _TAMIL_LATIN:
        return "ta-en"
    if words & _HINDI_LATIN:
        return "hi"
    return "en"


def reply_language(language, status):
    """en/ta/hi reply in kind; Tanglish replies in Tamil; low confidence or errors use English."""
    if status in ("LOW_CONFIDENCE", "ERROR"):
        return "en"
    return "ta" if language == "ta-en" else language
