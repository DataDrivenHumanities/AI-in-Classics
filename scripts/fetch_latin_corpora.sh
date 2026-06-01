#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-data/external}"

mkdir -p "$ROOT_DIR"

echo "[fetch] Target dir: $ROOT_DIR"

fetch_repo () {
  local url="$1"
  local dest="$2"

  if [[ -d "$dest/.git" ]]; then
    echo "[fetch] Already cloned: $dest"
    return 0
  fi

  echo "[fetch] Cloning $url -> $dest"
  git clone --depth 1 "$url" "$dest"
}

fetch_repo "https://github.com/OpenGreekAndLatin/Latin.git" "$ROOT_DIR/ogl_latin"
fetch_repo "https://github.com/PerseusDL/canonical-latinLit.git" "$ROOT_DIR/perseus_latin"
fetch_repo "https://github.com/CIRCSE/LT4HALA.git" "$ROOT_DIR/evalatin"

echo "[fetch] Done."

