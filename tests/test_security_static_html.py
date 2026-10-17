"""
靜態前端頁面的 XSS 回歸檢查（純文字掃描，不需瀏覽器）。
"""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "src" / "static"


def _script(name: str) -> str:
    text = (STATIC / name).read_text(encoding="utf-8")
    return "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", text, flags=re.S))


def test_error_messages_are_not_injected_as_html():
    for name in ("index.html", "upload_test.html"):
        js = _script(name)
        # 例外訊息不得未經跳脫直接放進 innerHTML 模板
        assert not re.search(r"innerHTML\s*\+?=\s*`[^`]*\$\{e(rror)?\.message\}", js), name


def test_no_inline_event_handlers_with_interpolation():
    for name in ("index.html", "upload_test.html"):
        js = _script(name)
        assert not re.search(r"on\w+=\"[^\"]*\$\{", js), name


def test_index_escapes_company_names():
    js = _script("index.html")
    assert "function esc(" in js
    assert "${c.company_name}" not in js
    assert "${p.company_name}" not in js
    assert "${p.company_name||\"\"}" not in js


def test_upload_page_escapes_and_sends_token():
    js = _script("upload_test.html")
    assert "function escapeHtml(" in js
    for raw in ("${preview.filename}", "${metadata.filename}", "${warning}", "${error}", "${suggestion}"):
        assert raw not in js
    # 狀態訊息以 textContent 呈現
    assert "statusDiv.innerHTML" not in js
    # 上傳與狀態查詢都帶上 Authorization
    assert js.count("authHeaders()") >= 2
    assert "localStorage.getItem('aev_token')" in js
