import argparse, os, glob, time, socket, ssl
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google_auth_httplib2
import httplib2

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--service-account-json", required=True)
    p.add_argument("--root-folder-id", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout seconds")
    p.add_argument("--retries", type=int, default=6, help="Max retries on network errors")
    p.add_argument("--limit-total", type=int, default=0, help="Limit total per-lemma uploads for testing (0 = no limit)")
    return p.parse_args()

def backoff_sleep(i):
    time.sleep(min(2 ** i, 16))

def safe_execute(req, retries):
    for i in range(retries + 1):
        try:
            # Also ask googleapiclient to retry HTTP 5xx, 429 internally.
            return req.execute(num_retries=retries)
        except (TimeoutError, socket.timeout, ssl.SSLError) as e:
            if i == retries:
                raise
            backoff_sleep(i)

def safe_resumable_upload(request, retries):
    response = None
    i = 0
    while response is None:
        try:
            status, response = request.next_chunk(num_retries=retries)
        except (TimeoutError, socket.timeout, ssl.SSLError):
            if i >= retries:
                raise
            backoff_sleep(i)
            i += 1
    return response

def main():
    a = parse_args()

    creds = Credentials.from_service_account_file(a.service_account_json, scopes=["https://www.googleapis.com/auth/drive"])
    # Explicit HTTP timeout for all requests
    http = httplib2.Http(timeout=a.timeout)
    authed_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)

    svc = build("drive", "v3", http=authed_http, cache_discovery=False)

    root = safe_execute(
        svc.files().get(fileId=a.root_folder_id, fields="id,name,driveId", supportsAllDrives=True),
        a.retries,
    )
    drive_id = root.get("driveId")

    def get_or_create_folder(name, parent_id):
        q = (
            f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents and trashed = false"
        )
        res = safe_execute(
            svc.files().list(
                q=q,
                fields="files(id,name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="drive",
                driveId=drive_id,
                pageSize=10,
            ),
            a.retries,
        )
        items = res.get("files", [])
        if items:
            return items[0]["id"]
        meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
        created = safe_execute(
            svc.files().create(body=meta, fields="id", supportsAllDrives=True),
            a.retries,
        )
        return created["id"]

    def upload_csv(path, parent_id):
        body = {"name": os.path.basename(path), "parents": [parent_id]}
        media = MediaFileUpload(path, mimetype="text/csv", chunksize=1024 * 1024, resumable=True)
        request = svc.files().create(
            body=body, media_body=media, fields="id", supportsAllDrives=True
        )
        resp = safe_resumable_upload(request, a.retries)
        return resp["id"]

    # 1) aggregates/
    agg_id = get_or_create_folder("aggregates", a.root_folder_id)
    for name in ("lemmas.csv", "forms.csv"):
        pth = os.path.join(a.outdir, name)
        if os.path.exists(pth):
            upload_csv(pth, agg_id)

    # 2) letter folders a..z + other
    letters = {chr(c): get_or_create_folder(chr(c), a.root_folder_id) for c in range(ord("a"), ord("z") + 1)}
    other_id = get_or_create_folder("other", a.root_folder_id)

    # Upload each per-lemma CSV to lettered folder
    uploaded = 0
    for pth in glob.glob(os.path.join(a.outdir, "*.csv")):
        base = os.path.basename(pth)
        if base in ("lemmas.csv", "forms.csv"):
            continue
        if a.limit_total and uploaded >= a.limit_total:
            break
        stem = os.path.splitext(base)[0]
        first = (stem[:1] or "").lower()
        parent = letters.get(first, other_id)
        upload_csv(pth, parent)
        uploaded += 1

    print(f"Uploaded aggregates + {uploaded} per-lemma CSVs.")

if __name__ == "__main__":
    main()
