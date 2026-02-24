from __future__ import annotations

import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import psycopg
from psycopg.rows import dict_row


_WORD_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


def _strip_accents(s: str) -> str:
    if not s:
        return ""
    nf = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nf if not unicodedata.combining(ch))


def basic_norm_token(token: str) -> str:
    token = unicodedata.normalize("NFC", token or "").strip()
    token = token.strip("“”\"'`´‘’.,;:!?()[]{}<>—–-")
    token = token.lower()
    token = _strip_accents(token)
    return token


def _pos_bucket_from_scraped(pos: Optional[str]) -> str:
    """
    Map scraped POS strings to coarse buckets to match LatinAffectus POS.
    This should be conservative; return 'other' when unsure.
    """
    p = (pos or "").lower()
    if not p:
        return "other"
    # Important: "pronoun" contains the substring "noun". Handle pronouns first.
    if "pron" in p:
        return "other"
    if "verb" in p:
        return "verb"
    if "adv" in p:
        return "adv"
    if "adj" in p:
        return "adj"
    if "noun" in p or "substant" in p:
        return "noun"
    return "other"


def _pos_bucket_from_affectus(pos: Optional[str]) -> str:
    p = (pos or "").strip().lower()
    if p in {"noun", "n"}:
        return "noun"
    if p in {"adj", "a", "adjective"}:
        return "adj"
    if p in {"verb", "v"}:
        return "verb"
    if p in {"adv", "adverb"}:
        return "adv"
    return "other"


DEFAULT_NEGATORS = {
    "non",
    "nec",
    "neque",
    "nisi",
    "haud",
    "sine",
    "nemo",
    "nullus",
    "vix",
    "ne",
}

DEFAULT_SHIFTERS = {
    "valde",
    "nimis",
    "tam",
    "satis",
    "parum",
    "paene",
    "adeo",
    "magis",
    "minus",
}

# Conservative: keep small to avoid accidentally dropping meaningful content.
DEFAULT_STOPWORDS = {
    "et",
    "in",
    "de",
    "ad",
    "a",
    "ab",
    "e",
    "ex",
    "sed",
    "aut",
    "vel",
    "ut",
    "cum",
    "qui",
    "quae",
    "quod",
    "quo",
    "quam",
    "quom",
}


@dataclass(frozen=True)
class LatinLexiconAnnotatorConfig:
    top_k: int = 20
    drop_stopwords: bool = True
    stopwords: set[str] = field(default_factory=lambda: set(DEFAULT_STOPWORDS))
    negators: set[str] = field(default_factory=lambda: set(DEFAULT_NEGATORS))
    shifters: set[str] = field(default_factory=lambda: set(DEFAULT_SHIFTERS))
    enable_orthography_fallbacks: bool = True
    enable_enclitic_fallbacks: bool = True
    enclitics: tuple[str, ...] = ("que", "ve", "ne")


class LatinLexiconAnnotator:
    """
    Passage-level annotator for Phase 2 (testing-first, no LLM).

    Uses:
      - scraped lookup DB in `public.*` to map tokens -> lemma_key (`public.lemmas.lemma_nod`)
      - `lila.sentiment` (LatinAffectus) to attach polarity priors
    """

    def __init__(
        self,
        *,
        dsn: Optional[str] = None,
        config: Optional[LatinLexiconAnnotatorConfig] = None,
    ):
        self.config = config or LatinLexiconAnnotatorConfig()

        # Load DATABASE_URL from .env for local dev ergonomics.
        if dsn is None:
            try:
                from dotenv import load_dotenv  # type: ignore

                project_root = Path(__file__).resolve().parents[3]
                for env_path in (Path.cwd() / ".env", project_root / ".env"):
                    if env_path.exists():
                        load_dotenv(env_path)
                        break
            except Exception:
                pass
        self.dsn = (dsn or os.getenv("DATABASE_URL") or "").strip()
        if not self.dsn:
            raise ValueError("Set DATABASE_URL or pass dsn=...")

        self._conn = psycopg.connect(self.dsn, row_factory=dict_row)

        # Small optional caches (safe for dev/eval runs).
        self._lemma_to_sentiment_cache: dict[str, list[dict[str, Any]]] = {}

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self) -> "LatinLexiconAnnotator":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def tokenize(self, text: str) -> list[str]:
        text = unicodedata.normalize("NFC", text or "")
        raw_tokens = _WORD_RE.findall(text)
        out: list[str] = []
        for t in raw_tokens:
            tn = basic_norm_token(t)
            if not tn:
                continue
            out.append(tn)
        return out

    def _variant_enclitic_bases(self, token: str) -> list[str]:
        """
        Fallback: split enclitics like -que/-ve/-ne for lookup only.

        We do NOT change token counts; we only try the base form when the full token misses.
        """
        if not self.config.enable_enclitic_fallbacks:
            return []
        t = token or ""
        bases: list[str] = []
        for suf in self.config.enclitics:
            if suf and t.endswith(suf) and len(t) > (len(suf) + 2):
                bases.append(t[: -len(suf)])
        return bases

    def _variant_orthography(self, token: str) -> list[str]:
        """
        Fallback: try common Latin orthography variants for lookup only.

        - u/v: handle texts using V for both u and v (e.g., VBI -> UBI)
        - i/j: handle texts using j where DB uses i (or vice versa)

        We generate only a small number of deterministic variants to keep queries bounded.
        """
        if not self.config.enable_orthography_fallbacks:
            return []
        t = token or ""
        if not t:
            return []

        vowels = set("aeiouy")

        def _uv_heuristic(s: str) -> str:
            chars = list(s)
            for i, ch in enumerate(chars):
                nxt = chars[i + 1] if (i + 1) < len(chars) else ""
                # v used as vowel u when followed by consonant (e.g., vbi -> ubi)
                if ch == "v" and nxt and nxt not in vowels:
                    chars[i] = "u"
                # u used as consonant v when followed by vowel (e.g., uix -> vix; seruus -> servus)
                elif ch == "u" and nxt and nxt in vowels:
                    chars[i] = "v"
            return "".join(chars)

        out: list[str] = []

        uv = _uv_heuristic(t)
        if uv != t:
            out.append(uv)

        if "j" in t:
            out.append(t.replace("j", "i"))
        if "i" in t:
            out.append(t.replace("i", "j"))

        # combine with the u/v heuristic if it changed
        if uv != t:
            if "j" in uv:
                out.append(uv.replace("j", "i"))
            if "i" in uv:
                out.append(uv.replace("i", "j"))

        # stable de-dupe, preserve order
        seen: set[str] = set()
        uniq: list[str] = []
        for v in out:
            if v and v not in seen and v != t:
                seen.add(v)
                uniq.append(v)
        return uniq

    def _lookup_variants_for_token(self, token: str) -> list[str]:
        """
        Ordered lookup keys to try for a token, from highest confidence to lowest.
        """
        t = token or ""
        variants: list[str] = [t]

        # Orthography variants of the full token
        variants.extend(self._variant_orthography(t))

        # Enclitic base variants (and their orthography variants)
        for b in self._variant_enclitic_bases(t):
            variants.append(b)
            variants.extend(self._variant_orthography(b))

        # stable de-dupe, preserve order
        seen: set[str] = set()
        out: list[str] = []
        for v in variants:
            if not v or v in seen:
                continue
            seen.add(v)
            out.append(v)
        return out

    def _filter_tokens(self, tokens: Iterable[str]) -> list[str]:
        out: list[str] = []
        for t in tokens:
            if not t:
                continue
            if self.config.drop_stopwords and t in self.config.stopwords and t not in self.config.negators:
                continue
            out.append(t)
        return out

    def _lookup_forms_candidates(self, token_norms: list[str]) -> dict[str, list[int]]:
        if not token_norms:
            return {}
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT form_nod::text AS token, array_agg(DISTINCT lemma_id) AS lemma_ids
                FROM public.forms
                WHERE form_nod = ANY(%s)
                GROUP BY form_nod
                """,
                (token_norms,),
            )
            rows = cur.fetchall()
        out: dict[str, list[int]] = {}
        for r in rows:
            token = str(r["token"])
            lemma_ids = list(r["lemma_ids"] or [])
            out[token] = sorted(set(int(x) for x in lemma_ids))
        return out

    def _lookup_direct_lemmas(self, token_norms: list[str]) -> dict[str, int]:
        if not token_norms:
            return {}
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT lemma_nod::text AS token, id AS lemma_id
                FROM public.lemmas
                WHERE lemma_nod = ANY(%s)
                """,
                (token_norms,),
            )
            rows = cur.fetchall()
        return {str(r["token"]): int(r["lemma_id"]) for r in rows}

    def _fetch_lemmas_by_id(self, lemma_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not lemma_ids:
            return {}
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, lemma_nod::text AS lemma_nod, lemma_diac, pos
                FROM public.lemmas
                WHERE id = ANY(%s)
                """,
                (lemma_ids,),
            )
            rows = cur.fetchall()
        return {int(r["id"]): dict(r) for r in rows}

    def _fetch_sentiment_rows(self, lemma_keys: list[str]) -> dict[str, list[dict[str, Any]]]:
        """
        Returns mapping lemma_key -> list of affectus rows.
        """
        out: dict[str, list[dict[str, Any]]] = {k: [] for k in lemma_keys}
        if not lemma_keys:
            return out

        # Cache-aware fetch: query only missing lemma_keys.
        missing = [k for k in lemma_keys if k not in self._lemma_to_sentiment_cache]
        if missing:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      norm(lemma) AS lemma_key,
                      lemma AS lemma_raw,
                      pos,
                      polarity_score,
                      has_polarity,
                      provenance
                    FROM lila.sentiment
                    WHERE norm(lemma) = ANY(%s)
                    """,
                    (missing,),
                )
                rows = cur.fetchall()
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for r in rows:
                lk = str(r["lemma_key"])
                grouped[lk].append(
                    {
                        "lemma_raw": r["lemma_raw"],
                        "pos": r["pos"],
                        "polarity_score": float(r["polarity_score"]) if r["polarity_score"] is not None else None,
                        "has_polarity": r["has_polarity"],
                        "provenance": r["provenance"],
                        "pos_bucket": _pos_bucket_from_affectus(r["pos"]),
                    }
                )
            for k in missing:
                self._lemma_to_sentiment_cache[k] = grouped.get(k, [])

        for k in lemma_keys:
            out[k] = list(self._lemma_to_sentiment_cache.get(k, []))
        return out

    def annotate(self, text: str) -> dict[str, Any]:
        tokens_raw = self.tokenize(text)
        tokens = self._filter_tokens(tokens_raw)
        token_counts = Counter(tokens)
        unique_tokens = sorted(token_counts.keys())

        # Build a bounded set of lookup keys (token + fallbacks) and remember their priority per token.
        token_lookup_order: dict[str, list[str]] = {t: self._lookup_variants_for_token(t) for t in unique_tokens}
        all_lookup_keys: list[str] = sorted({k for ks in token_lookup_order.values() for k in ks})

        direct = self._lookup_direct_lemmas(all_lookup_keys)
        form_candidates = self._lookup_forms_candidates(all_lookup_keys)

        token_chosen_lemma_id: dict[str, int] = {}
        ambiguous_tokens: list[str] = []
        fallback_used: dict[str, str] = {}
        fallback_counts = {"orthography": 0, "enclitic": 0}

        for t in unique_tokens:
            chosen_key = ""
            cands: set[int] = set()
            for key in token_lookup_order.get(t, [t]):
                key_cands: set[int] = set()
                if key in direct:
                    key_cands.add(int(direct[key]))
                key_cands.update(int(x) for x in (form_candidates.get(key, []) or []))
                if key_cands:
                    chosen_key = key
                    cands = key_cands
                    break

            cand_list = sorted(cands)
            if not cand_list:
                continue
            if len(cand_list) > 1:
                ambiguous_tokens.append(t)

            # Track whether a fallback key was used (for debugging/coverage).
            if chosen_key and chosen_key != t:
                fallback_used[t] = chosen_key
                if any(t.endswith(suf) and chosen_key == t[: -len(suf)] for suf in self.config.enclitics if suf):
                    fallback_counts["enclitic"] += 1
                else:
                    fallback_counts["orthography"] += 1

            # deterministic choice: prefer direct lemma match for the chosen lookup key, else smallest lemma_id
            chosen = direct.get(chosen_key) or cand_list[0]
            token_chosen_lemma_id[t] = int(chosen)

        chosen_ids = sorted(set(token_chosen_lemma_id.values()))
        lemma_meta_by_id = self._fetch_lemmas_by_id(chosen_ids)

        # Aggregate by lemma_key
        lemma_counts: Counter[str] = Counter()
        lemma_pos_bucket: dict[str, str] = {}
        lemma_pos_raw: dict[str, Optional[str]] = {}

        lookup_hits = 0
        lookup_misses = 0
        for tok, cnt in token_counts.items():
            lemma_id = token_chosen_lemma_id.get(tok)
            if not lemma_id or lemma_id not in lemma_meta_by_id:
                lookup_misses += cnt
                continue
            lookup_hits += cnt
            m = lemma_meta_by_id[lemma_id]
            lemma_key = str(m["lemma_nod"])
            lemma_counts[lemma_key] += cnt
            pos_raw = m.get("pos")
            lemma_pos_raw[lemma_key] = pos_raw
            lemma_pos_bucket[lemma_key] = _pos_bucket_from_scraped(pos_raw)

        lemma_keys = sorted(lemma_counts.keys())

        sentiment_rows = self._fetch_sentiment_rows(lemma_keys)

        sentiment_hits: list[dict[str, Any]] = []
        affectus_hit_tokens = 0
        fallback_joins = 0

        for lemma_key in lemma_keys:
            rows = sentiment_rows.get(lemma_key, [])
            if not rows:
                continue
            bucket = lemma_pos_bucket.get(lemma_key, "other")
            matching = [r for r in rows if r.get("pos_bucket") == bucket and bucket != "other"]
            candidates = matching or rows
            # choose strongest signal by abs(score) (ties stable by order)
            def _score_key(r: dict[str, Any]) -> Tuple[float, str]:
                sc = r.get("polarity_score")
                return (abs(float(sc)) if sc is not None else 0.0, str(r.get("pos") or ""))

            chosen = sorted(candidates, key=_score_key, reverse=True)[0]
            pos_match = bool(matching)
            if not pos_match:
                fallback_joins += 1

            count = int(lemma_counts[lemma_key])
            score = chosen.get("polarity_score")
            importance = (abs(float(score)) if score is not None else 0.0) * count
            affectus_hit_tokens += count
            sentiment_hits.append(
                {
                    "lemma_key": lemma_key,
                    "count": count,
                    "scraped_pos": lemma_pos_raw.get(lemma_key),
                    "scraped_pos_bucket": bucket,
                    "affectus_lemma": chosen.get("lemma_raw"),
                    "affectus_pos": chosen.get("pos"),
                    "affectus_pos_bucket": chosen.get("pos_bucket"),
                    "polarity_score": score,
                    "has_polarity": chosen.get("has_polarity"),
                    "provenance": chosen.get("provenance"),
                    "pos_match": pos_match,
                    "importance": importance,
                }
            )

        sentiment_hits = sorted(sentiment_hits, key=lambda x: float(x.get("importance") or 0.0), reverse=True)
        top_k = sentiment_hits[: max(0, int(self.config.top_k))]

        negators = {n: int(token_counts.get(n, 0)) for n in sorted(self.config.negators) if token_counts.get(n, 0)}
        shifters = {s: int(token_counts.get(s, 0)) for s in sorted(self.config.shifters) if token_counts.get(s, 0)}

        total_tokens = sum(token_counts.values())
        affectus_hit_rate = (affectus_hit_tokens / lookup_hits) if lookup_hits else 0.0
        fallback_rate = (fallback_joins / len(sentiment_hits)) if sentiment_hits else 0.0

        return {
            "coverage": {
                "raw_token_count": int(len(tokens_raw)),
                "token_count": total_tokens,
                "unique_tokens": len(unique_tokens),
                "lookup_hits": lookup_hits,
                "lookup_misses": lookup_misses,
                "lookup_hit_rate": (lookup_hits / total_tokens) if total_tokens else 0.0,
                "affectus_hit_tokens": affectus_hit_tokens,
                "affectus_hit_rate": affectus_hit_rate,
                "sentiment_lemma_hits": len(sentiment_hits),
                "fallback_rate": fallback_rate,
                "ambiguous_tokens": len(ambiguous_tokens),
                "fallback_tokens_orthography": int(fallback_counts["orthography"]),
                "fallback_tokens_enclitic": int(fallback_counts["enclitic"]),
            },
            "negators": negators,
            "shifters": shifters,
            "top_k": top_k,
            "debug": {
                "ambiguous_token_examples": ambiguous_tokens[:25],
                "fallback_examples": dict(list(fallback_used.items())[:25]),
            },
        }

    def build_llm_payload(self, text: str) -> dict[str, Any]:
        """
        Build the compact "lexicon priors" payload intended for LLM injection.

        This intentionally excludes large debug fields.
        """
        res = self.annotate(text)
        cov = res.get("coverage") or {}
        hits = res.get("top_k") or []

        payload_hits: list[dict[str, Any]] = []
        for h in hits:
            score = h.get("polarity_score")
            # Sentiment priors only: skip neutral/empty rows to keep the payload small and focused.
            if score is None:
                continue
            try:
                sc = float(score)
                if sc == 0.0:
                    continue
            except Exception:
                continue

            payload_hits.append(
                {
                    "lemma": h.get("lemma_key"),
                    "pos": h.get("scraped_pos_bucket"),
                    "score": sc,
                    "count": int(h.get("count") or 0),
                }
            )

        affectus_hit_rate = cov.get("affectus_hit_rate", 0.0)
        try:
            affectus_hit_rate = round(float(affectus_hit_rate), 3)
        except Exception:
            affectus_hit_rate = 0.0

        return {
            "LEXICON_PRIORS": {
                "coverage": {
                    "tokens": int(cov.get("token_count", 0) or 0),
                    "lemmatized_tokens": int(cov.get("lookup_hits", 0) or 0),
                    "affectus_hit_tokens": int(cov.get("affectus_hit_tokens", 0) or 0),
                    "affectus_hit_rate": affectus_hit_rate,
                    "ambiguous_tokens": int(cov.get("ambiguous_tokens", 0) or 0),
                },
                "negators": res.get("negators") or {},
                "shifters": res.get("shifters") or {},
                "hits": payload_hits,
            }
        }
