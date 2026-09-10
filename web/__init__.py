"""Web package bootstrap for the NORYX7 browser shell.

The production web entrypoint serves ``index.html`` directly. Keep the UI
enhancement asset attached to that response so the design is applied even when
static-file mounting is intentionally minimal.
"""
from __future__ import annotations

from pathlib import Path

import fastapi.responses
from fastapi.responses import HTMLResponse

_ORIGINAL_FILE_RESPONSE = fastapi.responses.FileResponse
_WEB_DIR = Path(__file__).resolve().parent
_INDEX = _WEB_DIR / "index.html"
_UI = _WEB_DIR / "ui_enhancements.js"


def _serve_file(path, *args, **kwargs):
    if Path(path).resolve() == _INDEX.resolve():
        html = _INDEX.read_text(encoding="utf-8")
        if _UI.is_file():
            script = _UI.read_text(encoding="utf-8")
            marker = '<script src="/ui_enhancements.js"></script>'
            if marker not in html:
                html = html.replace("</body>", f"<script>{script}</script>\n<style>.top #clear:before{{content:'+' !important;border:0 !important;width:auto !important;height:auto !important;box-shadow:none !important;font-size:22px !important;line-height:1 !important;color:#cfe0ff !important}}.top #clear:after{{display:none !important}}</style>\n</body>", 1)
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
    return _ORIGINAL_FILE_RESPONSE(path, *args, **kwargs)


fastapi.responses.FileResponse = _serve_file
