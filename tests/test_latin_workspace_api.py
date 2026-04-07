import pytest


@pytest.mark.no_ollama
def test_samples_list_and_get():
    from fastapi.testclient import TestClient

    from src.app.server_fast import app

    client = TestClient(app)

    r = client.get("/api/samples/latin")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("samples"), list)
    assert len(data["samples"]) >= 1

    first = data["samples"][0]
    assert "id" in first and first["id"]

    r2 = client.get(f"/api/samples/latin/{first['id']}")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2.get("id") == first["id"]
    assert isinstance(data2.get("text"), str)
    assert len(data2["text"]) >= 0


@pytest.mark.no_ollama
def test_samples_path_traversal_blocked():
    from fastapi.testclient import TestClient

    from src.app.server_fast import app

    client = TestClient(app)
    r = client.get("/api/samples/latin/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code in (404, 422)


@pytest.mark.no_ollama
def test_text_extract_txt_roundtrip():
    from fastapi.testclient import TestClient

    from src.app.server_fast import app

    client = TestClient(app)
    content = b"Salve mundi.\n"
    r = client.post(
        "/api/text/extract",
        files={"file": ("hello.txt", content, "text/plain")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("filename") == "hello.txt"
    assert "Salve" in (data.get("text") or "")
    assert isinstance(data.get("warnings"), list)

