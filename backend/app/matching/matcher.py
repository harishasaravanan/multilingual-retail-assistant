"""Alias + fuzzy product matcher (SAD section 7.5, Tier 1).

Statuses follow API.md: OK, NOT_FOUND, LOW_CONFIDENCE.
Fuzzy scoring uses the standard library; swap in rapidfuzz later if needed.
"""
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.language.normalizer import clean, normalize

MATCH_MIN = 0.80         # at or above: accept
NOT_FOUND_BELOW = 0.55   # below: no such product
AMBIGUOUS_MARGIN = 0.04  # top two products closer than this: ask to repeat


@dataclass
class MatchResult:
    status: str
    product_id: str
    confidence: float
    query: str


def _score(query_tokens, alias):
    """Best similarity between the alias and any run of consecutive query words.

    A run whose words are all inside the alias ("sugar" for "sugar 1kg") also
    counts as a match, scored a little above MATCH_MIN. Products that share the
    word ("dove": shampoo and conditioner) then tie and are caught as ambiguous.
    """
    alias_words = set(alias.split())
    best = 0.0
    n = len(query_tokens)
    for i in range(n):
        for j in range(i + 1, n + 1):
            window = " ".join(query_tokens[i:j])
            s = SequenceMatcher(None, window, alias).ratio()
            if len(window) >= 4 and set(query_tokens[i:j]) <= alias_words:
                s = max(s, MATCH_MIN + 0.10 * len(window) / len(alias))
            if s > best:
                best = s
    return best


class Matcher:
    def __init__(self, conn):
        self.aliases = {}  # cleaned alias -> set of product ids
        for pid, name in conn.execute("SELECT product_id, name FROM products"):
            self._add(name, pid)
        for pid, alias in conn.execute("SELECT product_id, alias FROM aliases"):
            self._add(alias, pid)

    def _add(self, alias, pid):
        key = clean(alias)
        if key:
            self.aliases.setdefault(key, set()).add(pid)

    def _match_text(self, transcript):
        q = normalize(transcript).query
        if not q:
            return MatchResult("LOW_CONFIDENCE", None, 0.0, q)

        tokens = q.split()
        per_product = {}
        for alias, pids in self.aliases.items():
            s = _score(tokens, alias)
            for pid in pids:
                if s > per_product.get(pid, 0.0):
                    per_product[pid] = s

        ranked = sorted(per_product.items(), key=lambda kv: kv[1], reverse=True)
        top_id, top = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        top = round(top, 2)

        if top < NOT_FOUND_BELOW:
            return MatchResult("NOT_FOUND", None, top, q)
        if top < MATCH_MIN or (top - second) < AMBIGUOUS_MARGIN:
            return MatchResult("LOW_CONFIDENCE", None, top, q)
        return MatchResult("OK", top_id, top, q)

    def match(self, transcript):
        r = self._match_text(transcript)
        if not any(ord(c) >= 0x0900 for c in transcript):
            return r  # English is never changed
        from app.matching.phonetic import phonetic_match
        p = phonetic_match(transcript, self.aliases)
        q = getattr(r, "query", transcript)
        if r.status == "OK":
            if p and p[0] != r.product_id:  # the two methods disagree: do not guess
                return MatchResult("LOW_CONFIDENCE", None, r.confidence, q)
            return r
        return MatchResult("OK", p[0], p[1], q) if p else r
