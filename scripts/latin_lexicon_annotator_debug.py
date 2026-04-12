#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _read_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"File not found: {p}")
    return p.read_text(encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Debug-run LatinLexiconAnnotator on a passage.")
    ap.add_argument("--dsn", default="", help="Postgres DSN (defaults to DATABASE_URL/.env).")
    ap.add_argument("--file", default="", help="Path to a Latin text file.")
    ap.add_argument("--fixtures", default="", help="JSON file of passages (list of objects with 'text').")
    ap.add_argument("--top-k", type=int, default=20, help="Top-K sentiment hits to include.")
    ap.add_argument(
        "--payload-only",
        action="store_true",
        help="Print only the compact LLM-injection payload (LEXICON_PRIORS).",
    )
    ap.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON (no indentation/extra whitespace). Recommended with --payload-only.",
    )
    args = ap.parse_args()

    # Local import: add `src/Lemmatizer-LTN-LiLa/` to sys.path (hyphens are OK in paths).
    repo_root = Path(__file__).resolve().parents[1]
    lila_root = repo_root / "src" / "Lemmatizer-LTN-LiLa"
    sys.path.insert(0, str(lila_root))

    from rag.latin_lexicon_annotator import LatinLexiconAnnotator, LatinLexiconAnnotatorConfig  # type: ignore

    cfg = LatinLexiconAnnotatorConfig(top_k=args.top_k)
    with LatinLexiconAnnotator(dsn=(args.dsn or None), config=cfg) as ann:
        if args.fixtures:
            payload = json.loads(_read_text(args.fixtures))
            if not isinstance(payload, list):
                raise SystemExit("--fixtures must be a JSON list")
            for item in payload:
                if not isinstance(item, dict) or "text" not in item:
                    continue
                pid = item.get("id") or item.get("path") or "case"
                if args.payload_only:
                    res = ann.build_llm_payload(str(item["text"]))
                else:
                    res = ann.annotate(str(item["text"]))
                print(f"\n=== {pid} ===")
                if args.compact:
                    print(json.dumps(res, ensure_ascii=False, separators=(",", ":")))
                else:
                    print(json.dumps(res, ensure_ascii=False, indent=2))
            return

        if args.file:
            text = _read_text(args.file)
        else:
            text = sys.stdin.read()
        if args.payload_only:
            res = ann.build_llm_payload(text)
        else:
            res = ann.annotate(text)
        if args.compact:
            print(json.dumps(res, ensure_ascii=False, separators=(",", ":")))
        else:
            print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
