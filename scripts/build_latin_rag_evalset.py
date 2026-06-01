#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


WORD_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)

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
    "minime",
}

DEFAULT_ENCLITICS = ("que", "ve", "ne")
DEFAULT_ENCLITIC_FALSE_FRIENDS = {
    "itaque",
    "undique",
    "atque",
    "neque",  # treat as negator, not a split candidate
}

SKIP_TEI_TAGS = {
    "note",
    "bibl",
    "head",
    "fw",
    "pb",
    "lb",
    "milestone",
    "ref",
}


def _localname(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


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


def tokenize(text: str) -> List[str]:
    raw_tokens = WORD_RE.findall(unicodedata.normalize("NFC", text or ""))
    out: List[str] = []
    for t in raw_tokens:
        tn = basic_norm_token(t)
        if tn:
            out.append(tn)
    return out


def _collect_text_skipping(elem: ET.Element) -> str:
    """
    Collect visible text while skipping certain TEI tags (notes, headers, etc.).
    Keeps child tails so we don't lose surrounding punctuation/spacing completely.
    """
    parts: List[str] = []
    if _localname(elem.tag) not in SKIP_TEI_TAGS and elem.text:
        parts.append(elem.text)

    for child in list(elem):
        if _localname(child.tag) in SKIP_TEI_TAGS:
            if child.tail:
                parts.append(child.tail)
            continue
        parts.append(_collect_text_skipping(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _norm_ws(s: str) -> str:
    return " ".join((s or "").split())


def _find_tei_namespace(root: ET.Element) -> Dict[str, str]:
    if root.tag.startswith("{") and "}" in root.tag:
        return {"tei": root.tag.split("}", 1)[0].strip("{")}
    return {}


def _extract_cts_urn(root: ET.Element, ns: Dict[str, str]) -> str:
    # Try common TEI header patterns used in CapiTainS/Perseus/OGL.
    idnos: List[str] = []
    if ns:
        nodes = root.findall(".//tei:teiHeader//tei:idno", ns)
    else:
        nodes = root.findall(".//teiHeader//idno")
    for n in nodes:
        val = _norm_ws("".join(n.itertext()))
        if val:
            idnos.append(val)
    for v in idnos:
        if "urn:cts:" in v:
            return v[v.find("urn:cts:") :].strip()
    return ""


def extract_tei_passages(path: Path) -> Tuple[str, List[Dict[str, str]]]:
    """
    Returns (base_urn, passages) where passages is a list of {ref,text}.
    """
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return ("", [])

    root = tree.getroot()
    ns = _find_tei_namespace(root)
    base_urn = _extract_cts_urn(root, ns)
    if not base_urn:
        # CapiTainS-style corpora typically encode the CTS identifier in the filename.
        # Example: phi0474.phi013.perseus-lat2.xml -> urn:cts:latinLit:phi0474.phi013.perseus-lat2
        base_urn = f"urn:cts:latinLit:{path.stem}"

    if ns:
        body = root.find(".//tei:text/tei:body", ns)
        if body is None:
            body = root.find(".//tei:body", ns)
    else:
        body = root.find(".//text/body") or root.find(".//body")
    if body is None:
        return (base_urn, [])

    passages: List[Dict[str, str]] = []
    # Prefer paragraph-like units; fall back to body text if needed.
    candidates: List[ET.Element] = []
    for tag in ("p", "l", "ab"):
        if ns:
            candidates.extend(body.findall(f".//tei:{tag}", ns))
        else:
            candidates.extend(body.findall(f".//{tag}"))

    if not candidates:
        txt = _norm_ws(_collect_text_skipping(body))
        if txt:
            passages.append({"ref": "body", "text": txt})
        return (base_urn, passages)

    for idx, el in enumerate(candidates, start=1):
        txt = _norm_ws(_collect_text_skipping(el))
        if not txt:
            continue
        ref = el.get("{http://www.w3.org/XML/1998/namespace}id") or el.get("n") or str(idx)
        passages.append({"ref": ref, "text": txt})
    return (base_urn, passages)


def is_mostly_latin(tokens: Sequence[str], *, min_ratio: float = 0.9) -> bool:
    """
    Heuristic filter to avoid ingesting Greek/bilingual/garbled passages.

    After normalization, "Latin-like" tokens should mostly be ASCII a-z (plus a few
    editorial artifacts). If too many tokens contain non [a-z], skip.
    """
    if not tokens:
        return False
    latinish = 0
    for t in tokens:
        if re.fullmatch(r"[a-z]+", t or ""):
            latinish += 1
    return (latinish / len(tokens)) >= float(min_ratio)


def _has_enclitic_token(tokens: Sequence[str], enclitics: Sequence[str]) -> bool:
    for t in tokens:
        if t in DEFAULT_ENCLITIC_FALSE_FRIENDS:
            continue
        for suf in enclitics:
            if suf and t.endswith(suf) and len(t) > (len(suf) + 2):
                return True
    return False


def _has_uv_orthography(tokens: Sequence[str]) -> bool:
    # crude but useful: tokens like vbi/vna/vtrum show up in older editions.
    if any(t in {"vbi", "vna", "vtrum"} for t in tokens):
        return True
    # heuristic: token begins with v followed by consonant (vbi, vna, vtrum, etc.)
    return any(re.match(r"^v[^aeiouy]", t) for t in tokens)


def infer_tags(text: str, tokens: Sequence[str], enclitics: Sequence[str]) -> List[str]:
    tags: List[str] = []
    if any(t in DEFAULT_NEGATORS for t in tokens):
        tags.append("negation")
    if _has_enclitic_token(tokens, enclitics):
        tags.append("enclitic")
    if _has_uv_orthography(tokens):
        tags.append("orthography_uv")
    if len(tokens) < 60:
        tags.append("short")
    elif len(tokens) < 250:
        tags.append("medium")
    else:
        tags.append("long")
    return tags


def _iter_input_files(inputs: Sequence[str]) -> Iterator[Path]:
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    yield f
        elif p.is_file():
            yield p


def _load_evalatin_tsv(tsv_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames:
            return rows

        # best-effort column detection
        fields = {c.lower(): c for c in reader.fieldnames}
        text_col = (
            fields.get("text")
            or fields.get("sentence")
            or fields.get("sentence_text")
            or fields.get("latin")
            or fields.get("sent")
        )
        label_col = fields.get("label") or fields.get("sentiment") or fields.get("polarity")
        id_col = fields.get("sentence_id") or fields.get("id")

        if not text_col:
            return rows

        for i, r in enumerate(reader, start=1):
            text = (r.get(text_col) or "").strip()
            if not text:
                continue
            rows.append(
                {
                    "id": (r.get(id_col) or f"evalatin_{tsv_path.stem}_{i}").strip(),
                    "text": text,
                    "sentiment_label": (r.get(label_col) or "").strip() if label_col else "",
                }
            )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a LatinRagLexiconPassages-style JSON from local corpora.")
    ap.add_argument(
        "--in",
        dest="inputs",
        action="append",
        default=[],
        help="Input file/dir (repeatable). Typically: data/external/ogl_latin or data/external/perseus_latin",
    )
    ap.add_argument(
        "--evalatin-tsv",
        action="append",
        default=[],
        help="Optional EvaLatin TSV(s) to include (repeatable).",
    )
    ap.add_argument("--out", default="tests/LatinRagLexiconPassages.generated.json", help="Output JSON path.")
    ap.add_argument("--max", type=int, default=100, help="Max passages to emit.")
    ap.add_argument("--min-tokens", type=int, default=60, help="Min tokens per TEI passage.")
    ap.add_argument("--max-tokens", type=int, default=250, help="Max tokens per TEI passage.")
    ap.add_argument("--enclitics", default="que,ve,ne", help="Comma-separated enclitics for tagging.")
    ap.add_argument(
        "--allow-non-latin",
        action="store_true",
        help="Do not filter out Greek/bilingual passages (not recommended).",
    )
    args = ap.parse_args()

    enclitics = tuple([x.strip() for x in args.enclitics.split(",") if x.strip()]) or DEFAULT_ENCLITICS

    out: List[Dict[str, Any]] = []

    # EvaLatin first (if provided explicitly).
    for raw in args.evalatin_tsv:
        p = Path(raw)
        if not p.exists():
            continue
        for row in _load_evalatin_tsv(p):
            toks = tokenize(row["text"])
            entry: Dict[str, Any] = {
                "id": str(row["id"]),
                "text": row["text"],
                "tags": ["evalatin", "latin"] + infer_tags(row["text"], toks, enclitics),
                "source": {
                    "type": "evalatin_tsv",
                    "path": str(p),
                },
            }
            if row.get("sentiment_label"):
                entry["sentiment_label"] = row["sentiment_label"]
            out.append(entry)
            if len(out) >= int(args.max):
                break
        if len(out) >= int(args.max):
            break

    # TEI XML extraction (OGL / Perseus / any TEI directory)
    if len(out) < int(args.max):
        for f in _iter_input_files(args.inputs):
            if f.suffix.lower() != ".xml":
                continue
            base_urn, passages = extract_tei_passages(f)
            for i, psg in enumerate(passages, start=1):
                text = psg["text"]
                toks = tokenize(text)
                if not args.allow_non_latin and not is_mostly_latin(toks):
                    continue
                if len(toks) < int(args.min_tokens) or len(toks) > int(args.max_tokens):
                    continue
                entry = {
                    "id": f"{f.stem}:{psg.get('ref') or i}",
                    "text": text,
                    "tags": ["tei", "latin"] + infer_tags(text, toks, enclitics),
                    "source": {
                        "type": "tei_xml",
                        "path": str(f),
                        "base_urn": base_urn,
                        "ref": psg.get("ref") or str(i),
                    },
                }
                out.append(entry)
                if len(out) >= int(args.max):
                    break
            if len(out) >= int(args.max):
                break

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(out)} passages to {out_path}")


if __name__ == "__main__":
    main()
