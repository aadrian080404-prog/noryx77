from __future__ import annotations

import os
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel

from core.contracts import TaskSpec
from core.operational_runtime import OperationalNORYXRuntime
from noryx7_runtime.model_adapters.openrouter import OpenRouterAdapter
from noryx7_runtime.model_fabric import ModelFabric


app = FastAPI(title="NORYX7 API", version="0.1.0")
WEB_DIR = Path(__file__).resolve().parent
INDEX_FILE = WEB_DIR / "index.html"
ROBOTS_FILE = WEB_DIR / "robots.txt"


class ChatRequest(BaseModel):
    message: str


@lru_cache(maxsize=1)
def get_runtime() -> OperationalNORYXRuntime:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    adapter = OpenRouterAdapter(api_key=api_key)
    fabric = ModelFabric([adapter], runtime_id=f"api-{uuid.uuid4().hex}")
    return OperationalNORYXRuntime(model_fabric=fabric)


@app.get("/", include_in_schema=False)
def root():
    if not INDEX_FILE.is_file():
        raise HTTPException(status_code=500, detail="web_interface_missing")
    return FileResponse(INDEX_FILE, media_type="text/html; charset=utf-8")


@app.get("/robots.txt", include_in_schema=False)
def robots():
    if ROBOTS_FILE.is_file():
        return FileResponse(ROBOTS_FILE, media_type="text/plain; charset=utf-8")
    return PlainTextResponse("User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: /sitemap.xml\n")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    base = str(request.base_url).rstrip("/")
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{base}/</loc></url>'
        '</urlset>'
    )
    return Response(content=content, media_type="application/xml")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "noryx7"}


@app.post("/api/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    execution_id = f"api-exec-{uuid.uuid4().hex}"
    task = TaskSpec(
        task_id=f"api-task-{uuid.uuid4().hex}",
        task_type="chat",
        objective=message,
        input=message,
        risk_class="normal",
        execution_id=execution_id,
    )

    try:
        result = get_runtime().run_hypersynth(task)
        if not isinstance(result, dict):
            raise RuntimeError("malformed_runtime_result")
        if result.get("status") != "completed":
            verification = result.get("verification")
            reason = result.get("reason") or "noryx7_execution_rejected"
            if verification is not None:
                reason = getattr(verification, "reason", None) or reason
            raise HTTPException(status_code=502, detail=reason)

        response = result.get("result")
        if not isinstance(response, str) or not response.strip():
            raise RuntimeError("empty_noryx7_response")
        verification = result.get("verification")
        return {
            "response": response,
            "task_id": result.get("task_id"),
            "execution_id": result.get("execution_id"),
            "verification": verification.__dict__ if hasattr(verification, "__dict__") else verification,
            "orchestration_stage": result.get("orchestration_stage"),
            "agent_runtime": [
                {
                    "agent_id": item.agent_id,
                    "role": item.role,
                    "state": item.state,
                }
                for item in get_runtime().agent_runtime.status()
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
