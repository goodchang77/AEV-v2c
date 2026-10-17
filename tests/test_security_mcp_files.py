"""
MCP 文件處理工具的檔案存取限制測試（不需 DB / 網路）。
"""

import asyncio
import base64
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.mcp_server import server as server_module
from src.mcp_server.server import DocumentAccessError, MCPServer, read_upload_document

MAX = 1024


@pytest.fixture
def layout(tmp_path):
    root = tmp_path / "uploads"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.pdf"
    secret.write_bytes(b"%PDF-1.4 secret outside root")
    ok = root / "report.pdf"
    ok.write_bytes(b"%PDF-1.4 ok")
    return root, outside, secret, ok


@pytest.fixture
def open_spy(monkeypatch):
    """記錄 server 模組內的 open() 呼叫，用來證明被拒絕的檔案從未被讀取"""
    calls = []
    real_open = open

    def spy(path, *args, **kwargs):
        calls.append(str(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(server_module, "open", spy, raising=False)
    return calls


def test_file_inside_root_is_read(layout, open_spy):
    root, _, _, ok = layout
    assert read_upload_document("report.pdf", str(root), MAX) == b"%PDF-1.4 ok"
    assert read_upload_document(str(ok), str(root), MAX) == b"%PDF-1.4 ok"


def test_absolute_path_outside_root_rejected(layout, open_spy):
    root, _, secret, _ = layout
    with pytest.raises(DocumentAccessError):
        read_upload_document(str(secret), str(root), MAX)
    assert open_spy == []


@pytest.mark.parametrize("rel", ["../outside/secret.pdf", "sub/../../outside/secret.pdf", "/etc/passwd", ".", ""])
def test_traversal_rejected(layout, open_spy, rel):
    root, *_ = layout
    with pytest.raises(DocumentAccessError):
        read_upload_document(rel, str(root), MAX)
    assert open_spy == []


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_symlink_escaping_root_rejected(layout, open_spy):
    root, _, secret, _ = layout
    link = root / "link.pdf"
    link.symlink_to(secret)
    with pytest.raises(DocumentAccessError):
        read_upload_document("link.pdf", str(root), MAX)
    dir_link = root / "dirlink"
    dir_link.symlink_to(secret.parent, target_is_directory=True)
    with pytest.raises(DocumentAccessError):
        read_upload_document("dirlink/secret.pdf", str(root), MAX)
    assert open_spy == []


def test_oversize_rejected_without_reading(layout, open_spy):
    root, *_ = layout
    (root / "big.pdf").write_bytes(b"x" * (MAX + 1))
    with pytest.raises(DocumentAccessError):
        read_upload_document("big.pdf", str(root), MAX)
    assert open_spy == []


def test_disallowed_extension_and_directory_rejected(layout, open_spy):
    root, *_ = layout
    (root / "notes.txt").write_bytes(b"hello")
    (root / "folder.pdf").mkdir()
    for name in ("notes.txt", "folder.pdf", "missing.pdf"):
        with pytest.raises(DocumentAccessError):
            read_upload_document(name, str(root), MAX)
    assert open_spy == []


def test_error_message_does_not_reveal_path_or_existence(layout):
    root, _, secret, _ = layout
    msgs = set()
    for p in (str(secret), str(secret) + ".nope"):
        with pytest.raises(DocumentAccessError) as exc:
            read_upload_document(p, str(root), MAX)
        msgs.add(str(exc.value))
        assert str(secret.parent) not in str(exc.value)
    assert len(msgs) == 1  # 存在與不存在的外部檔案回傳相同訊息


def _server(root):
    return MCPServer(
        db_session=MagicMock(),
        cache_enabled=False,
        max_concurrent_tools=1,
        upload_root=str(root),
        max_document_size=MAX,
    )


def test_mcp_tool_rejects_outside_path_without_processing(layout, open_spy, monkeypatch):
    root, _, secret, _ = layout
    process = AsyncMock(return_value={"status": "success"})
    monkeypatch.setattr(server_module.FinancialPDFProcessor, "process_pdf", process)
    resp = asyncio.run(_server(root).execute_tool(
        "process_financial_document",
        {"document_type": "pdf", "document_source": "file_path", "document_data": str(secret)},
    ))
    assert resp.success is False
    assert "not allowed" in resp.error
    assert str(secret) not in resp.error
    assert open_spy == []
    process.assert_not_called()


def test_mcp_tool_processes_file_inside_root(layout, monkeypatch):
    root, *_ = layout
    process = AsyncMock(return_value={"status": "success", "financial_data": {}})
    monkeypatch.setattr(server_module.FinancialPDFProcessor, "process_pdf", process)
    resp = asyncio.run(_server(root).execute_tool(
        "process_financial_document",
        {"document_type": "pdf", "document_source": "file_path", "document_data": "report.pdf"},
    ))
    assert resp.success is True
    assert process.call_args.args[0] == b"%PDF-1.4 ok"


def test_mcp_tool_rejects_oversize_base64(layout, monkeypatch):
    root, *_ = layout
    process = AsyncMock(return_value={"status": "success"})
    monkeypatch.setattr(server_module.FinancialPDFProcessor, "process_pdf", process)
    payload = base64.b64encode(b"x" * (MAX * 2)).decode()
    resp = asyncio.run(_server(root).execute_tool(
        "process_financial_document",
        {"document_type": "pdf", "document_source": "base64", "document_data": payload},
    ))
    assert resp.success is False
    assert "too large" in resp.error
    process.assert_not_called()


def test_mcp_tool_generic_error_does_not_leak_exception_text(layout, monkeypatch):
    root, *_ = layout
    process = AsyncMock(side_effect=RuntimeError("internal-secret-detail"))
    monkeypatch.setattr(server_module.FinancialPDFProcessor, "process_pdf", process)
    resp = asyncio.run(_server(root).execute_tool(
        "process_financial_document",
        {"document_type": "pdf", "document_source": "file_path", "document_data": "report.pdf"},
    ))
    assert resp.success is False
    assert "internal-secret-detail" not in resp.error
    assert resp.metadata["error_id"] in resp.error
