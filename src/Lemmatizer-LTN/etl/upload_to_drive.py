import argparse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

p = argparse.ArgumentParser()
p.add_argument("--service-account-json", required=True)
p.add_argument("--folder-id", required=True)
p.add_argument("--files", nargs="+", required=True)
a = p.parse_args()

creds = Credentials.from_service_account_file(
    a.service_account_json,
    scopes=["https://www.googleapis.com/auth/drive.file"]
)
svc = build("drive","v3", credentials=creds)

for path in a.files:
    media = MediaFileUpload(path, mimetype="text/csv")
    meta = {"name": path.split("/")[-1], "parents":[a.folder_id]}
    svc.files().create(body=meta, media_body=media, fields="id").execute()
    print(f"Uploaded {path}")
