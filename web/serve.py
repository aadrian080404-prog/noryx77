from __future__ import annotations

import os
from pathlib import Path

import uvicorn

import web as web_package
from web import app as web_app
from web.system_protocol_routes import register_system_protocol_routes
from web.ui_transform import build_ui_index


SOURCE = Path(web_app.INDEX_FILE)
TARGET = Path('/tmp/noryx7-index.html')
web_app.INDEX_FILE = build_ui_index(SOURCE, TARGET)

# The package bootstrap wraps FileResponse for the canonical index path. The
# production server intentionally serves a transformed copy, so point the
# bootstrap at that same copy; otherwise runtime status, scrolling and UI
enhancements are silently bypassed in production.
web_package._INDEX = Path(web_app.INDEX_FILE)

# Browser/System Protocol and the existing web API use the same cached gateway
# instance. This is an adapter at the HTTP boundary, not a second runtime.
register_system_protocol_routes(web_app.app, web_app.get_gateway)


if __name__ == '__main__':
    uvicorn.run(
        web_app.app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', '8000')),
    )
