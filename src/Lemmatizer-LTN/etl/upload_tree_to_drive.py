#!/usr/bin/env python3
import os
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def build_drive(sa_path: str):
    """Build a Drive service client with drive scope."""
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    return build("drive", "v3", credentials=creds)


def ensure_folder_exists(svc, folder_id: str):
    """Verify that folder_id is a folder the service account can see."""
    try:
        meta = svc.files().get(
            fileId=folder_id,
            fields="id,name,mimeType,driveId",
            supportsAllDrives=True,
        ).execute()
    except HttpError as e:
        raise SystemExit(f"Cannot access folder ID '{folder_id}': {e}")

    if meta.get("mimeType") != "application/vnd.google-apps.folder":
        raise SystemExit(
            f"Target is not a folder: {folder_id} (mimeType={meta.get('mimeType')})"
        )
    return meta


def get_or_create_child_folder(svc, parent_id: str, name: str) -> str:
    """Return id of child folder 'name' under parent_id, creating it if missing."""
    # NOTE: we assume `name` has no single quotes; your names (A..Z, 'aggregates') are safe.
    q = (
        f"name = '{name}' and "
        f"'{parent_id}' in parents and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        "trashed = false"
    )
    res = svc.files().list(
        q=q,
        spaces="drive",
        fields="files(id,name)",
        pageSize=1,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    f = svc.files().create(
        body=meta,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    print(f"Created folder '{name}' (id {f['id']}) under {parent_id}")
    return f["id"]


def upsert_file(svc, parent_id: str, local_path: Path, existing_files_cache: Dict[Tuple[str, str], str] = None, cache_lock: Lock = None):
    """Create or update a CSV file by name within parent_id.
    
    Args:
        svc: Drive service
        parent_id: Parent folder ID
        local_path: Path to local CSV file
        existing_files_cache: Optional dict mapping (parent_id, name) -> file_id
        cache_lock: Optional lock for thread-safe cache access
    """
    name = local_path.name
    cache_key = (parent_id, name)
    
    # Check cache first (thread-safe read)
    if existing_files_cache:
        if cache_lock:
            with cache_lock:
                fid = existing_files_cache.get(cache_key)
        else:
            fid = existing_files_cache.get(cache_key)
        
        if fid:
            media = MediaFileUpload(str(local_path), mimetype="text/csv", resumable=False)
            svc.files().update(
                fileId=fid,
                media_body=media,
                supportsAllDrives=True,
            ).execute()
            return ("update", name, fid)
    
    # Query for existing file
    q = (
        f"name = '{name}' and "
        f"'{parent_id}' in parents and "
        "trashed = false"
    )
    res = svc.files().list(
        q=q,
        spaces="drive",
        fields="files(id,name)",
        pageSize=1,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
    ).execute()
    files = res.get("files", [])

    media = MediaFileUpload(str(local_path), mimetype="text/csv", resumable=False)

    if files:
        fid = files[0]["id"]
        svc.files().update(
            fileId=fid,
            media_body=media,
            supportsAllDrives=True,
        ).execute()
        # Update cache (thread-safe write)
        if existing_files_cache:
            if cache_lock:
                with cache_lock:
                    existing_files_cache[cache_key] = fid
            else:
                existing_files_cache[cache_key] = fid
        return ("update", name, fid)
    else:
        meta = {"name": name, "parents": [parent_id]}
        f = svc.files().create(
            body=meta,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        fid = f["id"]
        # Update cache (thread-safe write)
        if existing_files_cache:
            if cache_lock:
                with cache_lock:
                    existing_files_cache[cache_key] = fid
            else:
                existing_files_cache[cache_key] = fid
        return ("create", name, fid)


def pick_letter(name: str) -> str:
    """Pick the first alphabetic character from the basename as A–Z bucket."""
    stem = Path(name).stem
    for ch in stem:
        if ch.isalpha():
            return ch.lower()
    return "misc"


def collect_csv_paths(files_args: List[str]) -> list[Path]:
    """Expand --files: accept files or directories, gather all *.csv."""
    paths: list[Path] = []
    for inp in files_args:
        p = Path(inp)
        if p.is_dir():
            for root, _, filenames in os.walk(p):
                for fn in filenames:
                    if fn.lower().endswith(".csv"):
                        paths.append(Path(root) / fn)
        elif p.is_file() and p.suffix.lower() == ".csv":
            paths.append(p)
        else:
            # ignore non-CSV paths
            pass

    # de-duplicate & sort
    uniq = sorted({p.resolve() for p in paths})
    return uniq


def upload_worker(args_tuple: Tuple) -> Tuple[str, str, str]:
    """Worker function for parallel uploads."""
    svc, parent_id, local_path, existing_files_cache, cache_lock, print_lock = args_tuple
    try:
        result = upsert_file(svc, parent_id, local_path, existing_files_cache, cache_lock)
        with print_lock:
            action, name, fid = result
            print(f"[{action}] {name} -> id {fid} in folder {parent_id}")
        return result
    except Exception as e:
        with print_lock:
            print(f"[ERROR] Failed to upload {local_path.name}: {e}")
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--service-account-json", required=True)
    ap.add_argument("--folder-id", required=True, help="Root Drive folder ID")
    ap.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="CSV file paths OR directories to scan for *.csv",
    )
    ap.add_argument(
        "--aggregates-folder-name",
        default="aggregates",
        help="Name of subfolder to hold lemmas.csv/forms.csv",
    )
    ap.add_argument(
        "--no-letter-folders",
        action="store_true",
        help="Don't split CSVs into letter subfolders (useful when uploading pre-aggregated letter files)",
    )
    ap.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of parallel upload workers (default: 10)",
    )
    args = ap.parse_args()

    svc = build_drive(args.service_account_json)
    ensure_folder_exists(svc, args.folder_id)
    root_id = args.folder_id

    paths = collect_csv_paths(args.files)
    if not paths:
        print("No CSV files found to upload.")
        return

    print(f"Found {len(paths)} CSV files to upload")
    print(f"Using {args.max_workers} parallel workers")

    # Aggregates folder (for lemmas.csv, forms.csv)
    agg_id = get_or_create_child_folder(svc, root_id, args.aggregates_folder_name)

    # Cache for letter subfolders
    letter_cache: dict[str, str] = {}
    letter_cache_lock = Lock()

    def letter_folder(letter: str) -> str:
        if letter not in letter_cache:
            with letter_cache_lock:
                # Double-check after acquiring lock
                if letter not in letter_cache:
                    letter_cache[letter] = get_or_create_child_folder(svc, root_id, letter)
        return letter_cache[letter]

    # Determine folder structure
    if args.no_letter_folders:
        # All CSVs go to aggregates folder (no letter subfolders)
        print("Using flat structure (all files in aggregates folder)")
        letters_needed = set()
        parent_id_for_all = agg_id
    else:
        # Pre-create all letter folders to avoid contention
        print("Pre-creating letter folders...")
        letters_needed = set()
        for p in paths:
            name = p.name
            if name not in ("lemmas.csv", "forms.csv"):
                bucket = pick_letter(name)
                letters_needed.add(bucket)
        
        for letter in sorted(letters_needed):
            letter_folder(letter)
        print(f"Created/prepared {len(letters_needed)} letter folders")
        parent_id_for_all = None

    # Prepare upload tasks
    existing_files_cache: Dict[Tuple[str, str], str] = {}
    cache_lock = Lock()
    print_lock = Lock()
    
    upload_tasks = []
    for p in paths:
        name = p.name
        if name in ("lemmas.csv", "forms.csv"):
            parent_id = agg_id
        elif args.no_letter_folders:
            parent_id = parent_id_for_all
        else:
            bucket = pick_letter(name)
            parent_id = letter_folder(bucket)
        
        upload_tasks.append((svc, parent_id, p, existing_files_cache, cache_lock, print_lock))

    # Upload in parallel
    start_time = time.time()
    completed = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_task = {executor.submit(upload_worker, task): task for task in upload_tasks}
        
        for future in as_completed(future_to_task):
            completed += 1
            if completed % 100 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = len(upload_tasks) - completed
                eta = remaining / rate if rate > 0 else 0
                print(f"Progress: {completed}/{len(upload_tasks)} files uploaded "
                      f"({rate:.1f} files/sec, ETA: {eta/60:.1f} min)")
            
            try:
                future.result()
            except Exception as e:
                failed += 1
                task = future_to_task[future]
                print(f"[ERROR] Failed: {task[2].name} - {e}")

    elapsed = time.time() - start_time
    print(f"\nUpload complete!")
    print(f"  Total files: {len(upload_tasks)}")
    print(f"  Successful: {completed - failed}")
    print(f"  Failed: {failed}")
    print(f"  Total time: {elapsed/60:.1f} minutes")
    print(f"  Average rate: {len(upload_tasks)/elapsed:.1f} files/sec")


if __name__ == "__main__":
    main()
