#!/usr/bin/env python3
import os
import argparse
from pathlib import Path
from typing import List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def build_drive(sa_path: str):
    """Build a Drive service client with drive.file scope."""
    scopes = ["https://www.googleapis.com/auth/drive.file"]
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


def upsert_file(svc, parent_id: str, local_path: Path):
    """Create or update a CSV file by name within parent_id."""
    name = local_path.name
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
        print(f"[update] {name} in folder {parent_id}")
    else:
        meta = {"name": name, "parents": [parent_id]}
        f = svc.files().create(
            body=meta,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        print(f"[create] {name} -> id {f['id']} in folder {parent_id}")


def pick_letter(name: str) -> str:
    """Pick the first alphabetic character from the basename as A–Z bucket."""
    stem = Path(name).stem
    for ch in stem:
        if ch.isalpha():
            return ch.upper()
    return "MISC"


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
    args = ap.parse_args()

    svc = build_drive(args.service_account_json)
    ensure_folder_exists(svc, args.folder_id)
    root_id = args.folder_id

    paths = collect_csv_paths(args.files)
    if not paths:
        print("No CSV files found to upload.")
        return

    # Aggregates folder (for lemmas.csv, forms.csv)
    agg_id = get_or_create_child_folder(svc, root_id, args.aggregates_folder_name)

    # Cache for letter subfolders
    letter_cache: dict[str, str] = {}

    def letter_folder(letter: str) -> str:
        if letter not in letter_cache:
            letter_cache[letter] = get_or_create_child_folder(svc, root_id, letter)
        return letter_cache[letter]

    # Upload all CSVs: lemmas/forms -> aggregates; others -> letter folders
    for p in paths:
        name = p.name
        if name in ("lemmas.csv", "forms.csv"):
            upsert_file(svc, agg_id, p)
        else:
            bucket = pick_letter(name)  # e.g., "A", "B", ...
            parent_id = letter_folder(bucket)
            upsert_file(svc, parent_id, p)


if __name__ == "__main__":
    main()
