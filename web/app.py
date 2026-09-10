from __future__ import annotations

import os
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel

from core.limits import RuntimeLimits
from core.system_identity import CANONICAL_SYSTEM_IDENTITY
from core.operational_runtime import OperationalNORYXRuntime
from core.user_understanding import UnderstandingConsent, UserUnderstandingEngine
from gateway.auth import SessionError
from gateway.server import NoryxGateway
from gateway.runtime_adapter import RuntimeAdapter
from noryx7_runtime.model_adapters.openrouter import OpenRouterAdapter
from noryx7_runtime.model_fabric import ModelFabric

app = FastAPI(title="NORYX7 API", version="0.2.0")
WEB_DIR = Path(__file__).resolve().parent
INDEX_FILE = WEB_DIR / "index.html"
ROBOTS_FILE = WEB_DIR / "robots.txt"
WEB_CLIENT_ID = "noryx-web"


class ChatRequest(BaseModel):
    message: str


class GatewaySessionRequest(BaseModel):
    bootstrap_token: str
    client_id: str


class GatewayExecuteRequest(BaseModel):
    input: str
    execution_id: str | None = None


def _operational_limits() -> RuntimeLimits:
    raw = os.environ.get("NORYX7_MAX_TASK_SECONDS", "120.0")
    try:
        seconds = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("NORYX7_MAX_TASK_SECONDS is invalid") from exc
    return RuntimeLimits(max_task_seconds=seconds)


@lru_cache(maxsize=1)
def get_runtime() -> OperationalNORYXRuntime:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    adapter = OpenRouterAdapter(api_key=api_key, timeout_seconds=120.0)
    fabric = ModelFabric([adapter], runtime_id=f"api-{uuid.uuid4().hex}")
    journal_path = os.environ.get("NORYX7_STATE_JOURNAL_PATH") or None
    understanding = UserUnderstandingEngine(
        consent=UnderstandingConsent.PRE_INTERACTION,
    )
    return OperationalNORYXRuntime(
        limits=_operational_limits(),
        model_fabric=fabric,
        state_journal_path=journal_path,
        user_understanding=understanding,
    )


@lru_cache(maxsize=1)
def get_gateway() -> NoryxGateway:
    return NoryxGateway(runtime_adapter=RuntimeAdapter(runtime=get_runtime()))


def _web_session_token() -> str:
    bootstrap = os.environ.get("NORYX_GATEWAY_BOOTSTRAP_TOKEN", "")
    if not bootstrap:
        raise RuntimeError("NORYX_GATEWAY_BOOTSTRAP_TOKEN is not configured")
    result = get_gateway().create_session(
        bootstrap_token=bootstrap,
        client_id=WEB_CLIENT_ID,
    )
    token = result.get("session_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("web_gateway_session_invalid")
    return token


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
    content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + f"<url><loc>{base}/</loc></url></urlset>"
    return Response(content=content, media_type="application/xml")


@app.get("/api/identity")
def identity():
    return {
        "system_id": CANONICAL_SYSTEM_IDENTITY.system_id,
        "creator": CANONICAL_SYSTEM_IDENTITY.creator,
        "creator_role": CANONICAL_SYSTEM_IDENTITY.creator_role,
        "creator_relationship": CANONICAL_SYSTEM_IDENTITY.creator_relationship,
        "provenance": CANONICAL_SYSTEM_IDENTITY.provenance,
    }


@app.get("/health")
def health():
    runtime = get_runtime()
    statuses = runtime.heartbeat_agents()
    return {
        "status": "healthy" if runtime.agent_runtime.online else "degraded",
        "service": "noryx7",
        "system_id": CANONICAL_SYSTEM_IDENTITY.system_id,
        "creator": CANONICAL_SYSTEM_IDENTITY.creator,
        "agents": [{"agent_id": item.agent_id, "role": item.role, "state": item.state} for item in statuses],
    }


@app.get("/v1/health")
def gateway_health():
    try:
        return get_gateway().health()
    except Exception as exc:
        import logging
        logging.getLogger("noryx7.gateway").exception("Gateway health initialization failed")
        raise HTTPException(
            status_code=503,
            detail=f"gateway_runtime_unhealthy:{type(exc).__name__}",
        ) from exc


@app.post("/v1/session")
def gateway_session(request: GatewaySessionRequest):
    try:
        return get_gateway().create_session(
            bootstrap_token=request.bootstrap_token,
            client_id=request.client_id,
        )
    except SessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="gateway_auth_failure") from exc


@app.post("/v1/execute")
def gateway_execute(request: GatewayExecuteRequest, http_request: Request):
    authorization = http_request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authorization_required")
    try:
        return get_gateway().execute(
            session_token=authorization[7:],
            text=request.input,
            execution_id=request.execution_id,
        )
    except SessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="gateway_runtime_failure") from exc


@app.post("/api/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")
    try:
        result = get_gateway().execute(
            session_token=_web_session_token(),
            text=message,
            execution_id=f"web-exec-{uuid.uuid4().hex}",
        )
        return {
            "response": result["result"],
            "system_id": result["system_id"],
            "creator": result["creator"],
            "task_id": result["task_id"],
            "execution_id": result["execution_id"],
            "client_id": result["client_id"],
            "verification": result["verification"],
            "agent_runtime": [
                {"agent_id": item.agent_id, "role": item.role, "state": item.state}
                for item in get_runtime().agent_runtime.status()
            ],
        }
    except SessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="web_gateway_runtime_failure") from exc
