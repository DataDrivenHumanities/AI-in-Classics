import os
import sys
import argparse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

p = argparse.ArgumentParser()
p.add_argument("--service-account-json", required=True)
p.add_argument("--folder-id", required=True, help="Drive folder ID (not URL)")
p.add_argument("--files", nargs="+", required=True,
               help="One or more CSV file paths OR directories to scan for *.csv")
a = p.parse_args()

creds = Credentials.from_service_account_file(
    a.service_account_json,
    scopes=["https://www.googleapis.com/auth/drive"]
)
svc = build("drive", "v3", credentials=creds)

# 0) Validate folder ID and access. Useful fields: name, mimeType, driveId.
try:
    folder_meta = svc.files().get(
        fileId=a.folder_id,
        fields="id,name,mimeType,driveId",
        supportsAllDrives=True
    ).execute()
    if folder_meta.get("mimeType") != "application/vnd.google-apps.folder":
        raise SystemExit(f"Target is not a folder: {a.folder_id} (mimeType={folder_meta.get('mimeType')})")
except HttpError as e:
    # 404/403 here usually means the service account lacks access or the ID is wrong.
    raise SystemExit(
        f"Cannot access folder ID '{a.folder_id}'. "
        f"Make sure it's the raw folder ID and that the service account is a member "
        f"(share the folder with the service account email). Under Shared Drives, "
        f'ensure "supportsAllDrives" is used. Original error: {e}'
    )

# 1) Expand inputs: accept directories and gather *.csv
paths = []
for inp in a.files:
    if os.path.isdir(inp):
        for root, _, files in os.walk(inp):
            for fn in files:
                if fn.lower().endswith(".csv"):
                    paths.append(os.path.join(root, fn))
    else:
        paths.append(inp)

paths = sorted(set(p for p in paths if os.path.isfile(p)))
if not paths:
    print("No CSV files found to upload.", file=sys.stderr)
    sys.exit(0)

# 2) Upload each file to the folder (supportsAllDrives handles Shared Drives)
for path in paths:
    media = MediaFileUpload(path, mimetype="text/csv")
    meta = {"name": os.path.basename(path), "parents": [a.folder_id]}
    try:
        svc.files().create(
            body=meta,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()
        print(f"Uploaded {path}")
    except HttpError as e:
        raise SystemExit(f"Upload failed for {path}: {e}")
