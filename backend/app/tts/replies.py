"""Spoken/on-screen reply text, built from the same result object as the screen.

Tamil and Hindi wording is a first draft and must be checked by a native speaker.
"""

_CURRENCY = {
    "en": {"INR": "rupees"},
    "ta": {"INR": "ரூபாய்"},
    "hi": {"INR": "रुपये"},
}

_TEXT = {
    "en": {
        "OK": "{product} is available in aisle {aisle}, shelf {shelf}. "
              "Follow the route on the screen.",
        "OUT_OF_STOCK": "{product} is currently unavailable.",
        "NOT_FOUND": "I could not find that product in this store.",
        "LOW_CONFIDENCE": "Sorry, please say that again.",
        "ERROR": "Sorry, something went wrong. Please try again.",
    },
    "ta": {
        "OK": "{product} நடைபாதை {aisle}, அடுக்கு {shelf} இல் உள்ளது. "
              "திரையில் உள்ள வழியைப் பின்பற்றவும்.",
        "OUT_OF_STOCK": "{product} தற்போது கிடைக்கவில்லை.",
        "NOT_FOUND": "இந்தப் பொருள் இந்தக் கடையில் கிடைக்கவில்லை.",
        "LOW_CONFIDENCE": "மன்னிக்கவும், மீண்டும் சொல்லுங்கள்.",
        "ERROR": "மன்னிக்கவும், ஏதோ தவறு நடந்தது. மீண்டும் முயற்சிக்கவும்.",
    },
    "hi": {
        "OK": "{product} गलियारा {aisle}, शेल्फ {shelf} में उपलब्ध है। "
              "कृपया स्क्रीन पर दिखाए गए रास्ते का अनुसरण करें।",
        "OUT_OF_STOCK": "{product} अभी उपलब्ध नहीं है।",
        "NOT_FOUND": "यह उत्पाद इस स्टोर में नहीं मिला।",
        "LOW_CONFIDENCE": "क्षमा करें, कृपया दोबारा बोलें।",
        "ERROR": "क्षमा करें, कुछ गलत हो गया। कृपया दोबारा कोशिश करें।",
    },
}


def build_reply(status, reply_language, result=None):
    lang = reply_language if reply_language in _TEXT else "en"
    table = _TEXT[lang]
    template = table.get(status) or _TEXT["en"][status]
    if result is None:
        return template
    unit = _CURRENCY.get(lang, _CURRENCY["en"]).get(result["currency"], result["currency"])
    return template.format(product=result["product"], aisle=result["aisle"],
                           shelf=result["shelf"], price=result["price"], unit=unit)


def spoken_language(status, reply_language):
    """Language the reply text is actually written in (falls back to English)."""
    lang = reply_language if reply_language in _TEXT else "en"
    return lang if status in _TEXT[lang] else "en"
