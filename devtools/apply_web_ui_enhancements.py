from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
TAG = '<script src="/ui_enhancements.js"></script>'

text = INDEX.read_text(encoding="utf-8")
if TAG not in text:
    marker = "</body>"
    if marker not in text:
        raise SystemExit("WEB_UI_PATCH_ABORTED: body marker not found")
    text = text.replace(marker, TAG + "\n" + marker, 1)
    INDEX.write_text(text, encoding="utf-8")
    print("WEB_UI_ENHANCEMENTS=APPLIED")
else:
    print("WEB_UI_ENHANCEMENTS=ALREADY_APPLIED")
