from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from PIL import Image, ImageOps, ImageFilter
from pdf2image import convert_from_bytes
import pytesseract
from pytesseract import Output

import io
import os
import sys
import time
import subprocess
import tempfile
import statistics

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from translation.groqTranslation import webTranslation

# ------------------------- FastAPI -------------------------
app = FastAPI()

# Allow local frontends to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------- Constants / helpers -------------------------
PAGE_SEP = "\n\n--- page break ---\n\n"
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".pdf"}

def infer_ext(filename: str) -> str:
    return (os.path.splitext(filename or "")[1] or "").lower()

def preprocess(img: Image.Image) -> Image.Image:
    """
    Gentle preprocessing:
      - 2.0x upscale (helps spacing)
      - grayscale + autocontrast
      - light UnsharpMask (keeps edges crisp)
      - larger right border to prevent tail clipping
    """
    w, h = img.size
    img = img.resize((int(w * 2.0), int(h * 2.0)), Image.LANCZOS)
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=2))
    #            left, top, right, bottom   (right made larger)
    img = ImageOps.expand(img, border=(12, 8, 36, 8), fill=255)
    return img

def _reconstruct_from_chars(
    img: Image.Image,
    psm: str = "7",
    lang: str = "lat",
    oem: str = "1",
    whitelist: str = ""
) -> str:
    """
    Char-box fallback: insert a space when the gap between adjacent chars
    exceeds an adaptive threshold from the median gap + width safeguard.
    """
    cfg = f"--oem {oem} --psm {psm} -c user_defined_dpi=400"
    if whitelist:
        cfg += f" -c tessedit_char_whitelist={whitelist}"

    boxes_txt = pytesseract.image_to_boxes(img, lang=lang, config=cfg)
    if not boxes_txt.strip():
        return ""

    # Parse char boxes
    chars = []
    for line in boxes_txt.splitlines():
        parts = line.strip().split()
        if len(parts) < 6:
            continue
        ch, x1, y1, x2, y2, _ = parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), parts[5]
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        w  = (x2 - x1)
        h  = (y2 - y1)
        chars.append((ch, x1, y1, x2, y2, cx, cy, w, h))  # (char, l,b,r,t, cx,cy, w,h)

    if not chars:
        return ""

    # Sort top->bottom, then left->right
    chars.sort(key=lambda c: (-c[6], c[5]))

    heights = [c[8] for c in chars if c[8] > 0]
    med_h   = statistics.median(heights) if heights else 1.0
    y_tol   = max(3, int(0.35 * med_h))  # looser so one real line doesn't split

    # Group into lines by y proximity
    lines, line = [], [chars[0]]
    for c in chars[1:]:
        if abs(c[6] - line[-1][6]) <= y_tol:
            line.append(c)
        else:
            lines.append(sorted(line, key=lambda t: t[5]))  # sort by x-center
            line = [c]
    lines.append(sorted(line, key=lambda t: t[5]))

    # Rebuild with adaptive spacing
    rebuilt = []
    for ln in lines:
        if not ln:
            continue

        gaps = []
        for prev, cur in zip(ln, ln[1:]):
            gap = cur[1] - prev[3]  # next.left - prev.right
            gaps.append(gap)

        median_gap = statistics.median(gaps) if gaps else 0
        avg_w      = max(1.0, sum(c[7] for c in ln) / len(ln))

        # More conservative about inserting spaces (prevents "pa rtes")
        thr_from_gaps  = max(3.0, median_gap * 1.8)  # was 1.6
        thr_from_width = 0.60 * avg_w                # was 0.50
        gap_threshold  = max(thr_from_gaps, thr_from_width)

        s = [ln[0][0]]
        for prev, cur in zip(ln, ln[1:]):
            gap = cur[1] - prev[3]
            if gap > gap_threshold:
                s.append(" ")
            s.append(cur[0])

        rebuilt.append("".join(s))

    # If multiple micro-lines but the image is a single text line, flatten
    if len(rebuilt) > 1:
        w, h = img.size
        if h < 0.4 * w:
            rebuilt = [" ".join(s for s in rebuilt if s.strip())]

    return "\n".join(rebuilt)

def ocr_tesseract_words(
    img: Image.Image,
    psm: str = "6",
    lang: str = "lat",
    oem: str = "1",
    whitelist: str = ""
) -> str:
    """
    Two-pass TSV strategy:
      1) TSV with requested PSM (e.g., 7 for single line)
      2) If collapsed, TSV with PSM 6 (paragraph) to force words
      3) If still collapsed, char-box fallback
      Best-of heuristic: prefer TSV unless char fallback is clearly longer (>=10%).
    """
    def _tsv(psm_value: str):
        cfg = f"--oem {oem} --psm {psm_value} -c user_defined_dpi=400 -c preserve_interword_spaces=1"
        if whitelist:
            cfg += f" -c tessedit_char_whitelist={whitelist}"
        return pytesseract.image_to_data(img, lang=lang, config=cfg, output_type=Output.DICT)

    def _rebuild_from_tsv(data_dict):
        words_by_line, line_tokens, prev_key = [], [], None
        n = len(data_dict.get("text", []))
        token_count = 0
        for i in range(n):
            txt = (data_dict["text"][i] or "").strip()
            conf = data_dict["conf"][i]
            try:
                conf_val = int(conf) if isinstance(conf, str) and conf.strip().lstrip("-").isdigit() else int(conf)
            except Exception:
                conf_val = 0
            if not txt or conf_val < 0:
                continue

            token_count += 1
            key = (data_dict["block_num"][i], data_dict["par_num"][i], data_dict["line_num"][i])
            if prev_key is None:
                prev_key = key
            if key != prev_key:
                if line_tokens:
                    words_by_line.append(" ".join(line_tokens))
                    line_tokens = []
                prev_key = key
            line_tokens.append(txt)

        if line_tokens:
            words_by_line.append(" ".join(line_tokens))

        joined = "\n".join(words_by_line).strip()
        return token_count, joined

    # Pass A: user-requested PSM
    dataA = _tsv(psm)
    tokensA, joinedA = _rebuild_from_tsv(dataA)

    # If collapsed, retry with PSM 6 to force word segmentation
    if tokensA <= 1 or not joinedA or (" " not in joinedA and len(joinedA) > 8):
        dataB = _tsv("6")
        tokensB, joinedB = _rebuild_from_tsv(dataB)
        if tokensB > 1 and (" " in joinedB or len(joinedB) <= 8):
            # Best-of vs char fallback (require >=10% longer to switch)
            char_alt = _reconstruct_from_chars(img, psm=(psm or "7"), lang=lang, oem=oem, whitelist=whitelist)
            if char_alt and len(char_alt) >= int(len(joinedB) * 1.10):
                return char_alt
            return joinedB
        # Still collapsed -> char fallback
        return _reconstruct_from_chars(img, psm=(psm or "7"), lang=lang, oem=oem, whitelist=whitelist)

    # Normal success path -> compare with char fallback (require >=10% longer)
    char_alt = _reconstruct_from_chars(img, psm=(psm or "7"), lang=lang, oem=oem, whitelist=whitelist)
    if char_alt and len(char_alt) >= int(len(joinedA) * 1.10):
        return char_alt
    return joinedA

def ocr_image_pil(
    img_pil: Image.Image,
    psm: str = "6",
    lang: str = "lat",
    oem: str = "1",
    whitelist: str = ""
) -> str:
    img = preprocess(img_pil)
    return ocr_tesseract_words(img, psm=psm, lang=lang, oem=oem, whitelist=whitelist)

def ocr_tesseract(
    img_bytes: bytes,
    psm: str = "6",
    lang: str = "lat",
    oem: str = "1",
    whitelist: str = ""
) -> str:
    img = Image.open(io.BytesIO(img_bytes))
    img = preprocess(img)
    return ocr_tesseract_words(img, psm=psm, lang=lang, oem=oem, whitelist=whitelist)

def ocr_kraken(img_bytes: bytes, model_id: str | None = None) -> str:
    """
    Calls Kraken CLI; ensure 'kraken' is installed in the WSL env.
    (Single-image support; PDF+Kraken would require per-page temp files.)
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name
    try:
        cmd = ["kraken", "-i", tmp_path, "-", "segment", "-bl", "ocr"]
        if model_id:
            cmd += ["-m", model_id]
        out = subprocess.run(cmd, capture_output=True, check=True)
        return out.stdout.decode("utf-8", errors="ignore")
    finally:
        os.remove(tmp_path)

def ocr_bytes_auto(
    file_bytes: bytes,
    filename: str,
    psm: str,
    lang: str,
    engine: str,
    oem: str = "1",
    whitelist: str = ""
):
    """
    Handles PNG/JPG directly; if PDF, converts to images (one per page) then OCRs each.
    Returns (combined_text, meta_dict).
    """
    ext = infer_ext(filename)
    start = time.perf_counter()
    pages, per_page_ms = [], []

    if ext == ".pdf":
        images = convert_from_bytes(file_bytes, dpi=300)
        for img in images:
            t0 = time.perf_counter()
            text = ocr_image_pil(img, psm=psm, lang=lang, oem=oem, whitelist=whitelist)
            per_page_ms.append(int((time.perf_counter() - t0) * 1000))
            pages.append(text)
        combined = PAGE_SEP.join(pages)
        meta = {"pages": len(pages), "per_page_ms": per_page_ms}
    else:
        t0 = time.perf_counter()
        if engine.lower() == "kraken":
            combined = ocr_kraken(file_bytes, model_id=None)
        else:
            combined = ocr_tesseract(
                img_bytes=file_bytes,
                psm=psm,
                lang=lang,
                oem=oem,
                whitelist=whitelist,
            )
        meta = {"pages": 1, "per_page_ms": [int((time.perf_counter() - t0) * 1000)]}

    meta["duration_ms"] = int((time.perf_counter() - start) * 1000)
    meta["psm"] = str(psm)
    return combined, meta

# ------------------------- Routes -------------------------
@app.get("/ping")
def ping():
    return {"ok": True}

@app.post("/ocr")
async def ocr(
    file: UploadFile = File(...),
    engine: str = Form("tesseract"),   # "tesseract" | "kraken"
    psm: str = Form("6"),              # Tesseract PSM
    lang: str = Form("lat"),           # Latin
    oem: str = Form("1"),              # 1: LSTM (default). Use 0 only if legacy data is installed.
    kraken_model: str | None = Form(None),
    whitelist: str = Form("")          # optional: restrict charset
):
    filename = file.filename or ""
    ext = infer_ext(filename)
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload PNG/JPG/PDF.")

    file_bytes = await file.read()

    # Friendly guard for OEM 0 without legacy data
    if oem == "0" and not os.path.exists("/usr/share/tesseract-ocr/5/tessdata/lat.traineddata"):
        raise HTTPException(
            status_code=400,
            detail="OEM 0 (legacy) requested, but legacy Latin data is not installed. "
                   "Use oem=1 or install legacy 'lat.traineddata'."
        )

    try:
        if engine.lower() == "kraken" and ext == ".pdf":
            raise HTTPException(status_code=400, detail="Kraken + PDF not yet supported.")

        text, meta = ocr_bytes_auto(
            file_bytes=file_bytes,
            filename=filename,
            psm=psm,
            lang=lang,
            engine=engine,
            oem=oem,
            whitelist=whitelist
        )

        # Translate the OCR'd text to English
        translation = ""
        try:
            if text.strip():
                translation = webTranslation(text)
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Translation failed: {e}")
            translation = "Translation failed"

        return JSONResponse({"engine": engine, "lang": lang, "text": text, "translation": translation, "meta": meta})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

