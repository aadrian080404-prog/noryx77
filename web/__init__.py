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


_RUNTIME_STATUS_PATCH = """
<script>
(() => {
  async function refreshNoryxRuntimeStatus() {
    const dot = document.getElementById('statusDot');
    const status = document.getElementById('status');
    const model = document.getElementById('model');
    if (!dot || !status) return;
    try {
      const response = await fetch('/v1/health', { cache: 'no-store' });
      if (!response.ok) throw new Error('gateway_http_' + response.status);
      const health = await response.json();
      if (health.status !== 'ok' || health.runtime !== 'connected') throw new Error('gateway_not_connected');
      dot.className = 'dot';
      status.textContent = 'NORYX7 online';
      if (model && model.textContent.includes('Configurazione richiesta')) {
        model.innerHTML = '<span class="dot"></span> HYPERSYNTH CORE';
      }
    } catch (_) {
      try {
        const response = await fetch('/health', { cache: 'no-store' });
        if (!response.ok) throw new Error('health_http_' + response.status);
        const health = await response.json();
        if (health.status !== 'healthy') throw new Error('runtime_degraded');
        dot.className = 'dot';
        status.textContent = 'NORYX7 online';
        if (model && model.textContent.includes('Configurazione richiesta')) {
          model.innerHTML = '<span class="dot"></span> HYPERSYNTH CORE';
        }
      } catch (_) {
        dot.className = 'dot bad';
        status.textContent = 'Runtime non raggiungibile';
      }
    }
  }
  window.addEventListener('online', refreshNoryxRuntimeStatus);
  window.addEventListener('offline', refreshNoryxRuntimeStatus);
  refreshNoryxRuntimeStatus();
  setInterval(refreshNoryxRuntimeStatus, 30000);
})();
</script>
"""


_BROWSER_BEHAVIOR_PATCH = """
<script>
(() => {
  const style = document.createElement('style');
  style.textContent = `
    html, body { height: 100%; }
    body { overflow: hidden; }
    .app { height: 100dvh; min-height: 0; }
    .main { min-height: 0; }
    .workspace {
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      overscroll-behavior-y: contain;
      touch-action: pan-y;
      -webkit-overflow-scrolling: touch;
    }
    .chat { min-height: 0; }
  `;
  document.head.appendChild(style);

  // The original chat renderer always jumps to the bottom after every message.
  // Preserve the reader's position unless they were already near the bottom.
  const originalAdd = window.add;
  if (typeof originalAdd === 'function') {
    window.add = function(text, kind, meta) {
      const workspace = document.getElementById('workspace');
      const before = workspace ? workspace.scrollTop : 0;
      const nearBottom = workspace
        ? workspace.scrollHeight - workspace.scrollTop - workspace.clientHeight < 96
        : true;
      const result = originalAdd.apply(this, arguments);
      if (workspace && !nearBottom) {
        requestAnimationFrame(() => { workspace.scrollTop = before; });
      }
      return result;
    };
  }

  // Replace the browser's generic execution failure with a stable, user-facing
  // explanation when an existing high-risk capability is not configured.
  const originalFetch = window.fetch.bind(window);
  window.fetch = async function(input, init) {
    const response = await originalFetch(input, init);
    try {
      const url = typeof input === 'string' ? input : input?.url || '';
      if (url.endsWith('/api/chat') && !response.ok) {
        const clone = response.clone();
        const payload = await clone.json().catch(() => ({}));
        const detail = String(payload.detail || '');
        if (detail.includes('execution_failure') || detail.includes('web_gateway_runtime_failure')) {
          return new Response(JSON.stringify({
            detail: 'runtime_execution_failed: verifica provider, autorizzazione o capability configurata'
          }), { status: response.status, headers: {'Content-Type':'application/json'} });
        }
      }
    } catch (_) {}
    return response;
  };
})();
</script>
"""


def _serve_file(path, *args, **kwargs):
    if Path(path).resolve() == _INDEX.resolve():
        html = _INDEX.read_text(encoding="utf-8")
        if _UI.is_file():
            script = _UI.read_text(encoding="utf-8")
            marker = '<script src="/ui_enhancements.js"></script>'
            if marker not in html:
                html = html.replace("</body>", f"<script>{script}</script>\n<style>.top #clear:before{{content:'+' !important;border:0 !important;width:auto !important;height:auto !important;box-shadow:none !important;font-size:22px !important;line-height:1 !important;color:#cfe0ff !important}}.top #clear:after{{display:none !important}}</style>\n{_RUNTIME_STATUS_PATCH}\n{_BROWSER_BEHAVIOR_PATCH}\n</body>", 1)
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
    return _ORIGINAL_FILE_RESPONSE(path, *args, **kwargs)


fastapi.responses.FileResponse = _serve_file
