"""Tests for the generic file upload endpoint."""
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Minimal 1x1 PNG bytes (valid PNG header)
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal PDF header bytes
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n%%EOF"


def test_upload_png_returns_url(client, creator_token):
    """PNG upload returns 201 with url under /uploads/thumbnails/."""
    resp = client.post(
        "/api/uploads",
        files={"file": ("test.png", io.BytesIO(PNG_BYTES), "image/png")},
        data={"category": "thumbnails"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["url"].startswith("/uploads/thumbnails/")
    assert body["filename"] == "test.png"
    assert body["size"] == len(PNG_BYTES)


def test_upload_pdf_returns_url(client, creator_token):
    """PDF upload returns 201 with url under /uploads/."""
    resp = client.post(
        "/api/uploads",
        files={"file": ("doc.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["url"].startswith("/uploads/general/")


def test_upload_disallowed_extension(client, creator_token):
    """.exe file returns 400."""
    resp = client.post(
        "/api/uploads",
        files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"].lower()


def test_upload_too_large(client, creator_token):
    """File exceeding 50MB returns 400."""
    big = b"x" * (50 * 1024 * 1024 + 1)
    resp = client.post(
        "/api/uploads",
        files={"file": ("big.png", io.BytesIO(big), "image/png")},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 400


def test_trainee_cannot_upload(client, trainee_token):
    """Trainee token is rejected with 403."""
    resp = client.post(
        "/api/uploads",
        files={"file": ("img.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers={"Authorization": f"Bearer {trainee_token}"},
    )
    assert resp.status_code == 403


def test_upload_creates_file(client, creator_token):
    """Uploaded file is persisted on disk at the path returned in url."""
    resp = client.post(
        "/api/uploads",
        files={"file": ("img.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    url = resp.json()["url"]  # e.g. /uploads/general/abc123_img.png
    path = Path(url.lstrip("/"))   # uploads/general/abc123_img.png
    assert path.exists()
