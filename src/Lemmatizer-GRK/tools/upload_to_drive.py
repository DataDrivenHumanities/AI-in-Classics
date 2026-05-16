#!/usr/bin/env python3
import os
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time
import ssl

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Global SSL bypass - handles network firewalls cleanly
ssl._create_default_https_context = ssl._create_unverified_context

def build_drive(sa_path: str):
    """Build a Drive service client with drive scope."""
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    
    # We use the default, thread-safe transport. The global SSL bypass protects it.
    service = build("drive", "v3", credentials=creds)
    
    try:
        service.about().get(fields="user").execute()
        print("Successfully authenticated with Google Drive (SSL bypassed)")
    except Exception as e:
        print(f"Warning: Failed to verify Drive connection: {e}")
    
    return service

def ensure_folder_exists(svc, folder_id: str):
    try:
        meta = svc.files().get(
            fileId=folder_id,
            fields="id,name,mimeType,driveId",
            supportsAllDrives=True,
        ).execute()
    except HttpError as e:
        raise SystemExit(f"Cannot access folder ID '{folder_id}': {e}")

    if meta.get("mimeType") != "application/vnd.google-apps.folder":
        raise SystemExit(f"Target is not a folder: {folder_id}")
    return meta

def get_or_create_child_folder(svc, parent_id: str, name: str) -> str:
    q = (
        f"name = '{name}' and "
        f"'{parent_id}' in parents and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        "trashed = false"
    )
    res = svc.files().list(
        q=q, spaces="drive", fields="files(id,name)", pageSize=1,
        includeItemsFromAllDrives=True, supportsAllDrives=True,
    ).execute()
    
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    f = svc.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    print(f"Created folder '{name}' (id {f['id']}) under {parent_id}")
    return f["id"]

def upsert_file(svc, parent_id: str, local_path: Path, existing_files_cache: Dict[Tuple[str, str], str] = None, cache_lock: Lock = None, max_retries: int = 3):
    name = local_path.name
    cache_key = (parent_id, name)
    
    last_error = None
    for attempt in range(max_retries):
        try:
            fid = None
            if existing_files_cache:
                if cache_lock:
                    with cache_lock:
                        fid = existing_files_cache.get(cache_key)
                else:
                    fid = existing_files_cache.get(cache_key)
                
            # Non-resumable upload - perfectly safe for tiny CSV files
            media = MediaFileUpload(str(local_path), mimetype="text/csv", resumable=False)

            # 1. Update if we already know the File ID from cache
            if fid:
                request = svc.files().update(fileId=fid, media_body=media, supportsAllDrives=True)
                response = request.execute() # <-- Clean execute, no chunking loop!
                return ("update", name, fid)
            
            # 2. Query Google Drive if it's not in our cache
            q = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
            res = svc.files().list(
                q=q, spaces="drive", fields="files(id,name)",
                pageSize=1, includeItemsFromAllDrives=True, supportsAllDrives=True
            ).execute()
            files = res.get("files", [])

            # 3. Update if found in Drive, Create if brand new
            if files:
                fid = files[0]["id"]
                request = svc.files().update(fileId=fid, media_body=media, supportsAllDrives=True)
                response = request.execute()
                
                if existing_files_cache is not None:
                    if cache_lock:
                        with cache_lock:
                            existing_files_cache[cache_key] = fid
                    else:
                        existing_files_cache[cache_key] = fid
                return ("update", name, fid)
            else:
                meta = {"name": name, "parents": [parent_id]}
                request = svc.files().create(body=meta, media_body=media, fields="id", supportsAllDrives=True)
                response = request.execute()
                fid = response["id"]
                
                if existing_files_cache is not None:
                    if cache_lock:
                        with cache_lock:
                            existing_files_cache[cache_key] = fid
                    else:
                        existing_files_cache[cache_key] = fid
                return ("create", name, fid)
                
        except (ssl.SSLError, ConnectionError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise last_error
        except HttpError as e:
            raise e
            
    raise last_error if last_error else Exception("Unknown error")

def pick_letter(name: str) -> str:
    stem = Path(name).stem
    for ch in stem:
        if ch.isalpha():
            return ch.lower()
    return "misc"

def collect_csv_paths(files_args: List[str]) -> list[Path]:
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
    return sorted({p.resolve() for p in paths})

def upload_worker(args_tuple: Tuple) -> Tuple[str, str, str]:
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
    ap.add_argument("--folder-id", required=True)
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--aggregates-folder-name", default="aggregates")
    ap.add_argument("--use-aggregates-folder", action="store_true")
    ap.add_argument("--no-letter-folders", action="store_true")
    ap.add_argument("--skip-large-files", action="store_true")
    ap.add_argument("--max-workers", type=int, default=5)
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
    
    agg_id = get_or_create_child_folder(svc, root_id, args.aggregates_folder_name) if args.use_aggregates_folder else root_id

    letter_cache: dict[str, str] = {}
    letter_cache_lock = Lock()

    def letter_folder(letter: str) -> str:
        if letter not in letter_cache:
            with letter_cache_lock:
                if letter not in letter_cache:
                    letter_cache[letter] = get_or_create_child_folder(svc, root_id, letter)
        return letter_cache[letter]

    if args.no_letter_folders:
        parent_id_for_all = agg_id
    else:
        letters_needed = set()
        for p in paths:
            name = p.name
            if name not in ("lemmas.csv", "forms.csv"):
                letters_needed.add(pick_letter(name))
        
        for letter in sorted(letters_needed):
            letter_folder(letter)
        parent_id_for_all = None

    existing_files_cache: Dict[Tuple[str, str], str] = {}
    cache_lock = Lock()
    print_lock = Lock()
    
    upload_tasks = []
    for p in paths:
        name = p.name
        if args.skip_large_files and name in ("lemmas.csv", "forms.csv"):
            continue
        
        if name in ("lemmas.csv", "forms.csv"):
            parent_id = agg_id
        elif args.no_letter_folders:
            parent_id = parent_id_for_all
        else:
            parent_id = letter_folder(pick_letter(name))
        
        upload_tasks.append((svc, parent_id, p, existing_files_cache, cache_lock, print_lock))

    start_time = time.time()
    completed = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_task = {executor.submit(upload_worker, task): task for task in upload_tasks}
        for future in as_completed(future_to_task):
            try:
                future.result()
                completed += 1
            except Exception:
                failed += 1

    elapsed = time.time() - start_time
    print(f"\nUpload complete! Successful: {completed}, Failed: {failed}")
    if failed > 0:
        raise SystemExit(f"Upload failed: {failed}/{len(upload_tasks)} files failed")

if __name__ == "__main__":
    main()