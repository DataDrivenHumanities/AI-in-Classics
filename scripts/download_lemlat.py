import gdown

url = "https://drive.google.com/drive/folders/1fH6gv1Ph8CrlZ0NDInZh2cyEK2L4h-QV"
gdown.download_folder(
    url=url,
    output="./data/lila",
    quiet=False,
)
