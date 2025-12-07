#!/usr/bin/env python3
import os
import argparse
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def build_drive(sa_path: str, scopes):
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    return build("drive", "v3", credentials=creds)

def ensure_folder_exists(svc, folder_id: str):
    try:
        svc.files().get(
            fileId=folder_id,
            fields="id,name,mimeType,driveId",
            supportsAllDrives=True,
        ).execute()
    except HttpError as e:
        raise SystemExit(f"Cannot access folder ID '{folder_id}': {e}")

def upsert_csv(svc, folder_id: str, local_path: Path):
    name = local_path.name
    # Find existing by name under the same parent
    res = svc.files().list(
        q=f"name = '{name}' and '{folder_id}' in parents and trashed = false",
        spaces="drive",
        fields="files(id,name)",
        pageSize=1,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
    ).execute()
    media = MediaFileUpload(str(local_path), mimetype="text/csv", resumable=False)

    if res.get("files"):
        fid = res["files"][0]["id"]
        svc.files().update(
            fileId=fid,
            media_body=media,
            supportsAllDrives=True,
        ).execute()
        print(f"Updated: {name} (id {fid})")
    else:
        meta = {"name": name, "parents": [folder_id]}
        f = svc.files().create(
            body=meta,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        print(f"Created: {name} (id {f['id']})")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--service-account-json", required=True)
    ap.add_argument("--folder-id", required=True, help="Target Drive folder ID")
    ap.add_argument("--files", nargs="+", required=True, help="CSV files or directories containing CSVs")
    args = ap.parse_args()

    svc = build_drive(args.service_account_json, ["https://www.googleapis.com/auth/drive.file"])
    ensure_folder_exists(svc, args.folder_id)

    for path in args.files:
        p = Path(path)
        if p.is_dir():
            for csvp in sorted(p.glob("*.csv")):
                upsert_csv(svc, args.folder_id, csvp)
        elif p.is_file() and p.suffix.lower() == ".csv":
            upsert_csv(svc, args.folder_id, p)
        else:
            print(f"[skip] {p} (not a CSV file or directory)")

if __name__ == "__main__":
    main()
