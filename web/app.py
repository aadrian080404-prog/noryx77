from __future__ import annotations

import os
import uuid
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.contracts import TaskSpec
from core.runtime import NORYXRuntime
from noryx7_runtime.model_adapters.openrouter import OpenRouterAdapter
from noryx7_runtime.model_fabric import ModelFabric


app = FastAPI(
    title="NORYX7 API",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    message: str


@lru_cache(maxsize=1)
def get_runtime() -> NORYXRuntime:
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    adapter = OpenRouterAdapter(api_key=api_key)

    fabric = ModelFabric(
        [adapter],
        runtime_id=f"api-{uuid.uuid4().hex}",
    )

    return NORYXRuntime(
        model_fabric=fabric,
    )


@app.get("/")
def root():
    return {
        "name": "NORYX7",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "noryx7",
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="message must not be empty",
        )

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
        runtime = get_runtime()

        result = runtime.run_hypersynth(task)

        if not isinstance(result, dict):
            raise RuntimeError("malformed_runtime_result")

        if result.get("status") != "completed":
            verification = result.get("verification")

            reason = result.get("reason") or "noryx7_execution_rejected"

            if verification is not None:
                reason = getattr(
                    verification,
                    "reason",
                    None,
                ) or reason

            raise HTTPException(
                status_code=502,
                detail=reason,
            )

        response = result.get("result")

        if not isinstance(response, str) or not response.strip():
            raise RuntimeError("empty_noryx7_response")

        return {
            "response": response,
            "task_id": result.get("task_id"),
            "execution_id": result.get("execution_id"),
            "verification": (
                result["verification"].__dict__
                if hasattr(result.get("verification"), "__dict__")
                else result.get("verification")
            ),
            "orchestration_stage": result.get("orchestration_stage"),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
