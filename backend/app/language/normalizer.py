"""Turn an STT transcript into an intent and a product phrase (SAD section 7.5).

Works on any script. The language label is never used, so a wrong language ID
cannot change which product is matched.
"""
import unicodedata
from dataclasses import dataclass


def clean(text):
    """Unicode-normalise, lower-case, drop punctuation, keep letters/marks/digits."""
    t = unicodedata.normalize("NFKC", text).casefold()
    t = "".join(ch if unicodedata.category(ch)[0] in "LMN" else " " for ch in t)
    return " ".join(t.split())


_FILLER = """
where is are the a an do you have can get find show tell me please i want need looking for in store
enga enge engey engae ange irukku iruku irukkum irukka irukkuma kidaikkum kidaikum kidaikuma
venum vendum venumnu enakku ennakku sollunga solunga kaattunga
kahan kahaan kaha milega milegi milta hai hain mujhe chahiye batao bataiye dikhao kya kidhar
எங்கே எங்க எங்கு இருக்கு இருக்கும் இருக்கா கிடைக்கும் கிடைக்குமா வேண்டும் வேணும் எனக்கு சொல்லுங்க
कहाँ कहां मिलेगा मिलेगी मिलता है हैं मुझे चाहिए चाहिये बताओ बताइए दिखाओ क्या
"""
FILLER = set(clean(_FILLER).split())


@dataclass
class Normalized:
    raw: str
    text: str      # cleaned full transcript
    query: str     # product phrase with question/filler words removed
    intent: str = "FIND"


def normalize(transcript):
    text = clean(transcript or "")
    query = " ".join(w for w in text.split() if w not in FILLER)
    return Normalized(raw=transcript or "", text=text, query=query)
