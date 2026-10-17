"""
文件上傳端點安全性測試（不需 DB / Redis / 網路）。
"""

import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from src.api.endpoints import document_upload as du
from src.api.endpoints.auth import get_current_user
from src.main import app

PDF = ("report.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")
SECRET_DETAIL = "internal-secret-detail-/srv/app"


def _user_from_header(request: Request):
    uid = request.headers.get("X-Test-User")
    if not uid:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return SimpleNamespace(user_id=uid, is_active=True, role="user")


@pytest.fixture
def client():
    du.processing_results.clear()
    app.dependency_overrides[get_current_user] = _user_from_header
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)
    du.processing_results.clear()


def _as(user):
    return {"X-Test-User": user}


# ---------------------------------------------------------------------------
# 認證
# ---------------------------------------------------------------------------
def test_anonymous_requests_are_rejected(monkeypatch):
    process = AsyncMock()
    monkeypatch.setattr(du.pdf_processor, "process_pdf", process)
    c = TestClient(app)  # 不覆寫 get_current_user：走真實 OAuth2 驗證
    name, content, ctype = PDF
    r = c.post("/api/v1/documents/upload/financial-statement",
               files={"file": (name, io.BytesIO(content), ctype)})
    assert r.status_code == 401
    r = c.post("/api/v1/documents/test-extraction",
               files={"file": (name, io.BytesIO(content), ctype)})
    assert r.status_code == 401
    assert c.get("/api/v1/documents/processing-status/x").status_code == 401
    assert c.delete("/api/v1/documents/processing-result/x").status_code == 401
    process.assert_not_called()
    # 公開資訊端點維持可用
    assert c.get("/api/v1/documents/supported-formats").status_code == 200


# ---------------------------------------------------------------------------
# 擁有者綁定
# ---------------------------------------------------------------------------
def test_cross_user_get_and_delete_return_404(client):
    name, content, ctype = PDF
    r = client.post(
        "/api/v1/documents/upload/financial-statement",
        files={"file": (name, io.BytesIO(content), ctype)},
        data={"async_processing": "true"},
        headers=_as("alice"),
    )
    assert r.status_code == 200
    doc_id = r.json()["document_id"]

    assert client.get(f"/api/v1/documents/processing-status/{doc_id}", headers=_as("mallory")).status_code == 404
    assert client.delete(f"/api/v1/documents/processing-result/{doc_id}", headers=_as("mallory")).status_code == 404
    assert doc_id in du.processing_results  # 未被他人刪除

    assert client.get(f"/api/v1/documents/processing-status/{doc_id}", headers=_as("alice")).status_code == 200
    assert client.delete(f"/api/v1/documents/processing-result/{doc_id}", headers=_as("alice")).status_code == 200
    assert doc_id not in du.processing_results


def test_legacy_entry_without_owner_is_not_readable(client):
    du.processing_results["legacy"] = {"status": "completed", "progress": 100}
    assert client.get("/api/v1/documents/processing-status/legacy", headers=_as("alice")).status_code == 404


# ---------------------------------------------------------------------------
# 大小限制
# ---------------------------------------------------------------------------
def test_oversize_rejected_by_content_length_before_processing(client, monkeypatch):
    monkeypatch.setattr(du, "MAX_FILE_SIZE", 1024)
    monkeypatch.setattr(du, "REQUEST_BODY_SLACK", 512)
    process = AsyncMock()
    monkeypatch.setattr(du.pdf_processor, "process_pdf", process)
    for path in ("/api/v1/documents/upload/financial-statement", "/api/v1/documents/test-extraction"):
        r = client.post(path, files={"file": ("big.pdf", io.BytesIO(b"x" * 4096), "application/pdf")},
                        headers=_as("alice"))
        assert r.status_code == 413
        assert "檔案大小超過限制" in r.json()["detail"]
    process.assert_not_called()


def test_oversize_chunked_body_without_content_length_is_rejected(client, monkeypatch):
    monkeypatch.setattr(du, "MAX_FILE_SIZE", 1024)
    monkeypatch.setattr(du, "REQUEST_BODY_SLACK", 512)
    process = AsyncMock()
    monkeypatch.setattr(du.pdf_processor, "process_pdf", process)
    boundary = "testboundary"
    head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"big.pdf\"\r\n"
            "Content-Type: application/pdf\r\n\r\n").encode()
    tail = f"\r\n--{boundary}--\r\n".encode()

    def body():
        yield head
        for _ in range(8):
            yield b"x" * 1024
        yield tail

    r = client.post(
        "/api/v1/documents/upload/financial-statement",
        content=body(),
        headers={**_as("alice"), "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert r.status_code == 413
    process.assert_not_called()


class _CountingUpload:
    def __init__(self, total):
        self.remaining = total
        self.bytes_read = 0
        self.size = None

    async def read(self, n=-1):
        n = self.remaining if n < 0 else min(n, self.remaining)
        self.remaining -= n
        self.bytes_read += n
        return b"x" * n


def test_read_upload_limited_stops_early(monkeypatch):
    monkeypatch.setattr(du, "UPLOAD_CHUNK_SIZE", 100)
    up = _CountingUpload(total=10_000)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(du.read_upload_limited(up, limit=250))
    assert exc.value.status_code == 413
    assert up.bytes_read <= 250 + 100  # 超過上限後立即停止，不讀完整檔


def test_read_upload_limited_uses_declared_size(monkeypatch):
    up = _CountingUpload(total=10_000)
    up.size = 10_000
    with pytest.raises(HTTPException):
        asyncio.run(du.read_upload_limited(up, limit=250))
    assert up.bytes_read == 0


def test_read_upload_limited_accepts_small_file():
    up = _CountingUpload(total=200)
    assert asyncio.run(du.read_upload_limited(up, limit=250)) == b"x" * 200


# ---------------------------------------------------------------------------
# 錯誤訊息不外洩
# ---------------------------------------------------------------------------
def test_unexpected_error_body_is_generic(client, monkeypatch):
    monkeypatch.setattr(du.pdf_processor, "process_pdf", AsyncMock(side_effect=RuntimeError(SECRET_DETAIL)))
    name, content, ctype = PDF
    r = client.post("/api/v1/documents/upload/financial-statement",
                    files={"file": (name, io.BytesIO(content), ctype)}, headers=_as("alice"))
    assert r.status_code == 500
    assert SECRET_DETAIL not in r.text
    assert "error_id" in r.json()["detail"]

    r = client.post("/api/v1/documents/test-extraction",
                    files={"file": (name, io.BytesIO(content), ctype)}, headers=_as("alice"))
    assert r.status_code == 200
    assert r.json()["success"] is False
    assert SECRET_DETAIL not in r.text


def test_processor_error_message_not_echoed(client, monkeypatch):
    monkeypatch.setattr(du.pdf_processor, "process_pdf", AsyncMock(return_value={
        "status": "error", "error_message": SECRET_DETAIL, "financial_data": {},
        "extraction_methods": [], "metadata": {},
    }))
    name, content, ctype = PDF
    r = client.post("/api/v1/documents/upload/financial-statement",
                    files={"file": (name, io.BytesIO(content), ctype)}, headers=_as("alice"))
    assert r.status_code == 500
    assert SECRET_DETAIL not in r.text
    assert r.json()["error"]["code"] == "DOCUMENT_PROCESSING_FAILED"


def test_background_failure_message_is_generic(monkeypatch):
    du.processing_results.clear()
    monkeypatch.setattr(du.pdf_processor, "process_pdf", AsyncMock(side_effect=RuntimeError(SECRET_DETAIL)))
    asyncio.run(du.process_document_background("d1", b"%PDF", "a.pdf", owner_id="alice"))
    entry = du.processing_results["d1"]
    assert entry["status"] == "failed"
    assert entry["owner_id"] == "alice"
    assert SECRET_DETAIL not in entry["message"]
    du.processing_results.clear()


# ---------------------------------------------------------------------------
# 結果儲存有上限
# ---------------------------------------------------------------------------
def test_result_store_is_bounded_and_expires(monkeypatch):
    store = du._BoundedResultStore(max_entries=3, ttl_seconds=10)
    clock = [100.0]
    monkeypatch.setattr(du.time, "monotonic", lambda: clock[0])
    for i in range(5):
        store[f"d{i}"] = {"owner_id": "a"}
    assert list(store.keys()) == ["d2", "d3", "d4"]
    clock[0] += 11
    store.evict()
    assert len(store) == 0


# ---------------------------------------------------------------------------
# 解析器資源上限
# ---------------------------------------------------------------------------
def test_pdf_page_limit(monkeypatch):
    import fitz

    from src.services import pdf_processor as pp

    doc = fitz.open()
    for _ in range(3):
        doc.new_page()
    data = doc.tobytes()
    doc.close()

    monkeypatch.setattr(pp, "MAX_PDF_PAGES", 2)
    proc = pp.FinancialPDFProcessor()
    plumber = AsyncMock(return_value={})
    monkeypatch.setattr(proc, "_extract_with_pdfplumber", plumber)
    result = asyncio.run(proc.process_pdf(data, "many.pdf"))
    assert result["status"] == "error"
    plumber.assert_not_called()


def test_excel_sheet_and_row_limits(monkeypatch):
    import openpyxl

    from src.services import excel_processor as ep

    wb = openpyxl.Workbook()
    ws = wb.active
    for i in range(20):
        ws.append([f"營業收入{i}", 1000 + i])
    for name in ("s2", "s3"):
        wb.create_sheet(name)
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()

    proc = ep.FinancialExcelProcessor()
    monkeypatch.setattr(ep, "MAX_EXCEL_SHEETS", 2)
    assert asyncio.run(proc.process_excel(data, "a.xlsx"))["status"] == "error"

    monkeypatch.setattr(ep, "MAX_EXCEL_SHEETS", 10)
    monkeypatch.setattr(ep, "MAX_EXCEL_ROWS_PER_SHEET", 5)
    result = asyncio.run(proc.process_excel(data, "a.xlsx"))
    assert result["status"] == "success"
    assert result["metadata"]["total_rows"] <= 5
