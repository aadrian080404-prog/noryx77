from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from gateway.auth import SessionError
from gateway.server import NoryxGateway

router = APIRouter()


def register_system_protocol_routes(app: Any, gateway_provider: Any) -> None:
    """Attach the first-party NORYX System Protocol to the hosted FastAPI app.

    The route delegates to the same NoryxGateway instance used by /v1/execute;
    it never creates a second runtime or execution path.
    """
    if app is None or not callable(gateway_provider):
        raise TypeError("system_protocol_registration_requires_app_and_gateway")

    @app.post("/v1/browser/session")
    def browser_session(request: dict):
        try:
            return gateway_provider().create_browser_session(
                pairing_code=str(request.get("pairing_code", "")),
                client_id=str(request.get("client_id", "")),
            )
        except SessionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="noryx_system_auth_failure") from exc

    @app.post("/v1/system/execute")
    def system_execute(request: dict, http_request: Request):
        try:
            authorization = http_request.headers.get("Authorization", "")
            if not authorization.startswith("Bearer "):
                raise SessionError("authorization_required")
            return gateway_provider().execute_system(
                session_token=authorization[7:],
                envelope=request,
            )
        except SessionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="noryx_system_runtime_failure") from exc
