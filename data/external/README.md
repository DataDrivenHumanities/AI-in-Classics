# External Latin Corpora (Local-Only)

This folder is for **large third-party corpora** that you may clone/download locally for building evaluation fixtures.

It is intentionally **ignored by git** (except this README), so you can store gigabytes of XML/TSV data without bloating the repo.

## Recommended sources (download locally)

1) **OpenGreekAndLatin (OGL) Latin** (TEI XML, generally CC BY-SA 4.0)
2) **PerseusDL canonical-latinLit** (TEI XML, CC BY-SA 4.0)
3) **EvaLatin / CIRCSE** sentiment evaluation datasets (often CC BY-NC-SA; do not commit without checking)

Use the helper script:

- `scripts/fetch_latin_corpora.sh`

## Expected directory layout

After running the fetch script, you should have:

- `data/external/ogl_latin/`
- `data/external/perseus_latin/`
- `data/external/evalatin/`

## Why this is local-only

Even when licenses are permissive, these repos are large and may require:

- attribution files
- license preservation
- careful review of “mixed” licensing within a corpus

So the recommended workflow is:

1) keep corpora local-only under `data/external/`
2) extract a **small, attributable** subset into `tests/*.json` for automated evaluation

