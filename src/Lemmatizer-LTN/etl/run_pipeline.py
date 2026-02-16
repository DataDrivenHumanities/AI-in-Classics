#!/usr/bin/env python3
"""
OS-agnostic pipeline runner for Latin ETL.
Run with --phase <name> to run a single step (so Azure shows each step separately).
Phases: setup | scrape | upload_drive | download_drive | db
(aggregate is now built into scrape — no separate step needed)
Or run with no --phase to run all phases (legacy).
"""
import argparse
import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Repo root and project paths (works from any cwd if BUILD_SOURCES_DIRECTORY is set)
REPO_ROOT = Path(os.environ.get("BUILD_SOURCES_DIRECTORY", Path.cwd()))
ROOT = REPO_ROOT / "src" / "Lemmatizer-LTN"
VENV_DIR = REPO_ROOT / ".venv"
ETL = ROOT / "etl"
OUT = ROOT / "out"
OPS = ROOT / "ops"

def venv_python():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"

def run_cmd(cmd: list[str], cwd: Path | None = None, env: dict | None = None, timeout_minutes: int | None = None):
    cwd = cwd or REPO_ROOT
    full_env = {**os.environ, **(env or {})}
    timeout_sec = (timeout_minutes or 0) * 60 or None
    r = subprocess.run(cmd, cwd=cwd, env=full_env, timeout=timeout_sec)
    if r.returncode != 0:
        sys.exit(r.returncode)

def phase_setup():
    b64 = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
    if b64:
        (REPO_ROOT / "service_account.json").write_bytes(base64.b64decode(b64))
        print("Wrote service_account.json")
    if not VENV_DIR.exists():
        print("Creating venv...")
        run_cmd([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=REPO_ROOT)
    py = str(venv_python())
    run_cmd([py, "-m", "pip", "install", "-U", "pip"], cwd=REPO_ROOT)
    run_cmd([py, "-m", "pip", "install", "-r", str(ETL / "requirements.txt")], cwd=REPO_ROOT)
    print("Venv ready.")

def phase_scrape():
    testing = os.environ.get("TESTING", "false").lower() in ("true", "1", "yes")
    py = str(venv_python())
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.iterdir():
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
    scraper = ROOT / "tools" / "scrape_tables.py"
    if testing:
        args = [str(scraper), "--outdir", str(OUT), "--start", "1", "--step", "1", "--end", "10",
                "--index-concurrency", "4", "--lemma-concurrency", "8", "--delay", "0.05"]
    else:
        args = [str(scraper), "--outdir", str(OUT), "--index-concurrency", "4",
                "--lemma-concurrency", "4", "--delay", "0.5"]
    print("Running scraper:", " ".join(args))
    run_cmd([py] + args, cwd=REPO_ROOT, timeout_minutes=120)

def phase_aggregate():
    """Legacy: run aggregation separately (only needed if per-lemma CSVs exist)."""
    py = str(venv_python())
    run_cmd([py, str(ETL / "aggregate_out_to_csvs.py")], cwd=REPO_ROOT)
    run_cmd([py, str(ETL / "aggregate_by_letter.py")], cwd=REPO_ROOT)

def phase_upload_drive():
    drive_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if not drive_id:
        print("GOOGLE_DRIVE_FOLDER_ID not set, skipping upload")
        return
    py = str(venv_python())
    lemmas_csv = OUT / "lemmas.csv"
    forms_csv = OUT / "forms.csv"
    letter_dir = OUT / "by_letter"
    run_cmd([py, str(ETL / "upload_tree_to_drive.py"),
             "--service-account-json", str(REPO_ROOT / "service_account.json"),
             "--folder-id", drive_id,
             "--files", str(lemmas_csv), str(forms_csv), str(letter_dir),
             "--max-workers", "1", "--no-letter-folders"], cwd=REPO_ROOT, timeout_minutes=30)

def phase_download_drive():
    drive_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if not drive_id:
        print("GOOGLE_DRIVE_FOLDER_ID not set, skipping download")
        return
    py = str(venv_python())
    OUT.mkdir(parents=True, exist_ok=True)
    run_cmd([py, str(ETL / "download_from_drive.py"),
             "--service-account-json", str(REPO_ROOT / "service_account.json"),
             "--folder-id", drive_id, "--outdir", str(OUT),
             "--files", "lemmas.csv", "forms.csv"], cwd=REPO_ROOT, timeout_minutes=10)

def phase_db():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set, skipping schema and load")
        return
    py = str(venv_python())
    schema_path = OPS / "init_db.sql"
    run_cmd([py, str(ETL / "load_aggregates_to_postgres.py"),
             "--schema", str(schema_path), "--outdir", str(OUT), "--truncate"],
            cwd=REPO_ROOT, env={"DATABASE_URL": dsn}, timeout_minutes=30)

def main():
    parser = argparse.ArgumentParser(description="Latin ETL pipeline (OS-agnostic)")
    parser.add_argument(
        "--phase",
        choices=["setup", "scrape", "aggregate", "upload_drive", "download_drive", "db"],
        help="Run only this phase (for step-by-step Azure UI)",
    )
    args = parser.parse_args()

    if args.phase:
        phases = {
            "setup": phase_setup,
            "scrape": phase_scrape,
            "aggregate": phase_aggregate,
            "upload_drive": phase_upload_drive,
            "download_drive": phase_download_drive,
            "db": phase_db,
        }
        phases[args.phase]()
        print(f"Phase '{args.phase}' done.")
        return

    # No --phase: run all (legacy). Pipeline mode controls which phases run.
    pipeline_mode = os.environ.get("PIPELINE_MODE", "Full E2E Pipeline")
    scrape_or_upload_drive = pipeline_mode in ("Full E2E Pipeline", "Scrape + Upload to Drive")
    upload_db = pipeline_mode == "Upload to Database"
    full_or_db = pipeline_mode in ("Full E2E Pipeline", "Upload to Database")

    phase_setup()
    if scrape_or_upload_drive:
        phase_scrape()
        # Aggregation is now built into the scraper — lemmas.csv and forms.csv
        # are written directly at the end of scraping.
        phase_upload_drive()
    if upload_db:
        phase_download_drive()
    if full_or_db:
        phase_db()
    print("Pipeline done.")

if __name__ == "__main__":
    main()
