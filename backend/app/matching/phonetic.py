"""Fallback for Tamil/Devanagari transcripts: compare consonant skeletons."""
import re
from difflib import SequenceMatcher

TA = dict(zip("கசடதபமயரலவழளறனஜஷஸஹ", "kcttpmyrlvllrnsssh"))
TA.update({"ங": "n", "ஞ": "n", "ண": "n", "ந": "n", "ச": "s"})
HI = {}
for ch, v in zip("कखगघचछजझटठडढतथदधपफबभ", "kkkkssssttttttttpppp"):
    HI[ch] = v
for ch, v in zip("ङञणनमयरलवशषसह", "nnnnmyrlvsssh"):
    HI[ch] = v
HI.update({"ं": "n", "ँ": "n"})
DIGRAPHS = [("ph", "p"), ("th", "t"), ("sh", "s"), ("ch", "s"), ("ck", "k"),
            ("kh", "k"), ("gh", "k"), ("dh", "t"), ("bh", "p")]
LATIN = {"c": "k", "q": "k", "x": "ks", "z": "s", "j": "s", "g": "k", "b": "p",
         "d": "t", "f": "p", "w": "v"}
STOP = set("எங்கே எங்க இருக்கு இருக்கிறது இங்கே என்ன பொருள் இது कहा कहां मिलेगा में लेगा मेलेगा "
           "मेंगेगा where is the".split())
MIN, MARGIN = 0.85, 0.08


def skel(word):
    w = word.lower()
    for a, b in DIGRAPHS:
        w = w.replace(a, b)
    out = []
    for c in w:
        if c in TA:
            out.append(TA[c])
        elif c in HI:
            out.append(HI[c])
        elif c.isascii() and c.isalpha():
            out.append(LATIN.get(c, c))
    s = re.sub(r"[aeiouyh]", "", "".join(out))
    return re.sub(r"(.)\1+", r"\1", s)


def _score(qwords, alias):
    a = " ".join(x for x in map(skel, alias.split()) if x)
    q = [x for x in map(skel, qwords) if x]
    best = 0.0
    for i in range(len(q)):
        for j in range(i + 1, len(q) + 1):
            best = max(best, SequenceMatcher(None, " ".join(q[i:j]), a).ratio())
    return best


def phonetic_match(transcript, aliases):
    """aliases: {alias: set(product_id)}. Returns (product_id, score) or None."""
    q = [w for w in re.sub(r"[?.!,]", " ", transcript).split() if w not in STOP and w.lower() not in STOP]
    if not q:
        return None
    per = {}
    for alias, pids in aliases.items():
        s = _score(q, alias)
        for p in pids:
            per[p] = max(per.get(p, 0.0), s)
    ranked = sorted(per.items(), key=lambda kv: kv[1], reverse=True)
    if len(ranked) < 2 or ranked[0][1] < MIN or ranked[0][1] - ranked[1][1] < MARGIN:
        return None
    return ranked[0][0], round(ranked[0][1], 2)
