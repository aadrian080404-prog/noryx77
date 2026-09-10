from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from web import app as web_app
from web.ui_transform import build_ui_index


SOURCE = Path(web_app.INDEX_FILE)
TARGET = Path('/tmp/noryx7-index.html')
web_app.INDEX_FILE = build_ui_index(SOURCE, TARGET)


if __name__ == '__main__':
    uvicorn.run(
        web_app.app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', '8000')),
    )
