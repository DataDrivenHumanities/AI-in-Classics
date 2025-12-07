#!/usr/bin/env python3
"""Download CSV files from Google Drive."""
import os
import argparse
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io


def build_drive(sa_path: str):
    """Build a Drive service client with drive scope."""
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    service = build("drive", "v3", credentials=creds)
    
    try:
        service.about().get(fields="user").execute()
        print("Successfully authenticated with Google Drive")
    except Exception as e:
        print(f"Warning: Failed to verify Drive connection: {e}")
    
    return service


def find_file_in_folder(svc, folder_id: str, filename: str):
    """Find a file by name in a folder."""
    query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    try:
        results = svc.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()
        files = results.get("files", [])
        if files:
            return files[0]["id"]
        return None
    except Exception as e:
        print(f"Error searching for {filename}: {e}")
        return None


def download_file(svc, file_id: str, output_path: Path):
    """Download a file from Drive to local path."""
    try:
        request = svc.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download progress: {int(status.progress() * 100)}%")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(fh.getvalue())
        
        print(f"Downloaded: {output_path} ({output_path.stat().st_size:,} bytes)")
        return True
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Download CSV files from Google Drive")
    ap.add_argument("--service-account-json", required=True, help="Path to service account JSON")
    ap.add_argument("--folder-id", required=True, help="Google Drive folder ID containing the files")
    ap.add_argument("--outdir", required=True, help="Output directory for downloaded files")
    ap.add_argument("--files", nargs="+", default=["lemmas.csv", "forms.csv"], 
                    help="File names to download (default: lemmas.csv forms.csv)")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    svc = build_drive(args.service_account_json)
    
    print(f"Searching for files in folder: {args.folder_id}")
    for filename in args.files:
        print(f"\nLooking for: {filename}")
        file_id = find_file_in_folder(svc, args.folder_id, filename)
        if file_id:
            output_path = outdir / filename
            if download_file(svc, file_id, output_path):
                print(f"✓ Successfully downloaded {filename}")
            else:
                print(f"✗ Failed to download {filename}")
        else:
            print(f"✗ File not found: {filename}")


if __name__ == "__main__":
    main()

