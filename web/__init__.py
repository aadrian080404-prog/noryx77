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
_TAG = '<script src="/ui_enhancements.js"></script>'


def _serve_file(path, *args, **kwargs):
    if Path(path).resolve() == _INDEX.resolve():
        html = _INDEX.read_text(encoding="utf-8")
        if _UI.is_file() and _TAG not in html:
            html = html.replace("</body>", f"{_TAG}\n</body>", 1)
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
    if Path(path).resolve() == _UI.resolve():
        return fastapi.responses.Response(
            content=_UI.read_text(encoding="utf-8"),
            media_type="application/javascript; charset=utf-8",
            headers={"Cache-Control": "no-cache"},
        )
    return _ORIGINAL_FILE_RESPONSE(path, *args, **kwargs)


fastapi.responses.FileResponse = _serve_file
