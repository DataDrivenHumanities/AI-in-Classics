import os
import argparse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

p = argparse.ArgumentParser()
p.add_argument("--service-account-json", required=True)
p.add_argument("--folder-id", required=True)
p.add_argument("--files", nargs="+", required=True,
               help="One or more CSV file paths OR directories to scan for *.csv")
a = p.parse_args()

creds = Credentials.from_service_account_file(
    a.service_account_json,
    scopes=["https://www.googleapis.com/auth/drive.file"]
)
svc = build("drive", "v3", credentials=creds)

# Expand inputs: accept files or directories
paths = []
for inp in a.files:
    if os.path.isdir(inp):
        for root, _, files in os.walk(inp):
            for fn in files:
                if fn.lower().endswith(".csv"):
                    paths.append(os.path.join(root, fn))
    else:
        paths.append(inp)

# Dedup + stable order
for path in sorted(set(paths)):
    media = MediaFileUpload(path, mimetype="text/csv")
    meta = {"name": os.path.basename(path), "parents": [a.folder_id]}
    svc.files().create(body=meta, media_body=media, fields="id").execute()
    print(f"Uploaded {path}")
