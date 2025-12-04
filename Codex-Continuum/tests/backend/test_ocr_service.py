# tests/backend/test_ocr_service.py

import pytest
from PIL import Image
from fastapi.testclient import TestClient

import backend.ocr_service.app as ocr_service


def test_ping_endpoint_works():
    """Basic smoke test for the OCR FastAPI app."""
    app_instance = getattr(ocr_service, "app", None)
    assert app_instance is not None, "FastAPI app should exist in backend.ocr_service.app"

    client = TestClient(app_instance)
    resp = client.get("/ping")
    # Just verify the endpoint responds
    assert resp.status_code == 200


@pytest.mark.parametrize("mode", ["normal", "fallback"])
def test_ocr_tesseract_words_modes(monkeypatch, mode):
    """Exercise ocr_tesseract_words with mocked Tesseract in both normal and fallback cases."""
    img = Image.new("RGB", (10, 10))

    def fake_image_to_data(*args, **kwargs):
        if mode == "normal":
            # "Normal" TSV output with real words
            return {
                "text": ["lorem", "ipsum"],
                "conf": [90, 95],
                "block_num": [0, 0],
                "par_num": [1, 1],
                "line_num": [1, 1],
                "word_num": [1, 2],
            }
        else:
            # Collapsed TSV that should force internal fallback path
            return {
                "text": [""],
                "conf": [-1],
                "block_num": [0],
                "line_num": [0],
                "word_num": [0],
            }

    def fake_image_to_boxes(*args, **kwargs):
        # Simple char-box fallback
        return "a 0 0 5 5 0\nb 0 0 5 5 0"

    # Patch pytesseract inside the ocr_service module
    monkeypatch.setattr("backend.ocr_service.app.pytesseract.image_to_data", fake_image_to_data)
    monkeypatch.setattr("backend.ocr_service.app.pytesseract.image_to_boxes", fake_image_to_boxes)

    text = ocr_service.ocr_tesseract_words(img)

    assert isinstance(text, str)
    assert text.strip() != ""
