# Uploads:
#   - aggregates (lemmas.csv, forms.csv) → ROOT/aggregates/
#   - per-lemma CSVs                      → ROOT/a/.../z/ (or ROOT/other/)
import argparse, os, glob
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

p = argparse.ArgumentParser()
p.add_argument("--service-account-json", required=True)
p.add_argument("--root-folder-id", required=True)
p.add_argument("--outdir", required=True)
a = p.parse_args()

scopes = ["https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(a.service_account_json, scopes=scopes)
svc = build("drive","v3", credentials=creds)

root = svc.files().get(fileId=a.root_folder_id,
                       fields="id,name,driveId",
                       supportsAllDrives=True).execute()
drive_id = root.get("driveId")

def get_or_create_folder(name, parent_id):
    q = (f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
         f"and '{parent_id}' in parents and trashed = false")
    res = svc.files().list(q=q, fields="files(id,name)",
                           supportsAllDrives=True, includeItemsFromAllDrives=True,
                           corpora="drive", driveId=drive_id, pageSize=10).execute()
    items = res.get("files", [])
    if items:
        return items[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents":[parent_id]}
    f = svc.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return f["id"]

def upload_csv(path, parent_id):
    body = {"name": os.path.basename(path), "parents":[parent_id]}
    media = MediaFileUpload(path, mimetype="text/csv")
    svc.files().create(body=body, media_body=media, fields="id", supportsAllDrives=True).execute()

# 1) aggregates/
agg_id = get_or_create_folder("aggregates", a.root_folder_id)
for name in ("lemmas.csv","forms.csv"):
    pth = os.path.join(a.outdir, name)
    if os.path.exists(pth): upload_csv(pth, agg_id)

# 2) letter folders a..z + other
letters = {chr(c): get_or_create_folder(chr(c), a.root_folder_id)
           for c in range(ord('a'), ord('z')+1)}
other_id = get_or_create_folder("other", a.root_folder_id)

# Upload each per-lemma CSV to lettered folder
for pth in glob.glob(os.path.join(a.outdir, "*.csv")):
    base = os.path.basename(pth)
    if base in ("lemmas.csv","forms.csv"):
        continue
    first = (os.path.splitext(base)[0][:1] or "").lower()
    parent = letters.get(first, other_id)
    upload_csv(pth, parent)

print("Uploaded aggregates + per-lemma files into lettered folders.")
