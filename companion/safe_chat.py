"""A confined text-only companion endpoint for the local KripAI model."""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

# Fixed destination; never derive it from the request, headers, or model settings.
_LOCAL_URL = "http://127.0.0.1:17012/v1/chat/completions"
_MAX_BODY = 65536
_MAX_MODEL_RESPONSE = 1048576
_ALLOWED = {("POST", "/api/companion/safe-chat"), ("GET", "/api/companion/ping"),
            ("GET", "/api/companion/info")}


def companion_route_allowed(method: str, path: str) -> bool:
    return (method, path) in _ALLOWED


def _key_file() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise ValueError("local data unavailable")
    return Path(local) / "Odysseus-kripusek-data" / "private-model" / "llama-api-key.txt"


def _validate_messages(value):
    if not isinstance(value, dict) or set(value) != {"messages"}:
        raise ValueError("invalid request")
    messages = value["messages"]
    if not isinstance(messages, list) or not 1 <= len(messages) <= 16:
        raise ValueError("invalid messages")
    total = 0
    for item in messages:
        if not isinstance(item, dict) or set(item) != {"role", "content"}:
            raise ValueError("invalid message")
        role, content = item["role"], item["content"]
        if role not in ("user", "assistant") or not isinstance(content, str) or not 1 <= len(content) <= 8000:
            raise ValueError("invalid message")
        total += len(content)
    if total > 32000 or messages[-1]["role"] != "user":
        raise ValueError("invalid messages")
    return messages


async def safe_chat(request: Request):
    scopes = set(getattr(request.state, "api_token_scopes", []) or [])
    if not getattr(request.state, "api_token", False) or not {"chat", "companion"} <= scopes:
        raise HTTPException(403, "Companion token required")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > _MAX_BODY:
            raise HTTPException(413, "Request too large")
        chunks.append(chunk)
    try:
        messages = _validate_messages(json.loads(b"".join(chunks)))
    except (ValueError, UnicodeError, TypeError):
        raise HTTPException(422, "Invalid messages") from None
    try:
        key = _key_file().read_text(encoding="utf-8").strip()
        if not key or len(key) > 1024 or any(ord(c) < 33 or ord(c) > 126 for c in key):
            raise ValueError("invalid key")
    except (OSError, UnicodeError, ValueError):
        raise HTTPException(503, "Local model unavailable") from None
    try:
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False,
                                     timeout=httpx.Timeout(90.0, connect=3.0)) as client:
            async with client.stream("POST", _LOCAL_URL,
                headers={"Authorization": "Bearer " + key},
                json={"model": "local", "messages": messages, "stream": False, "max_tokens": 1024}) as response:
                if response.status_code != 200:
                    raise HTTPException(503, "Local model unavailable")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > _MAX_MODEL_RESPONSE:
                        raise HTTPException(502, "Invalid local model response")
        payload = json.loads(data)
        text = payload["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text or len(text) > 32768:
            raise ValueError("invalid response")
    except HTTPException:
        raise
    except (httpx.HTTPError, OSError):
        raise HTTPException(503, "Local model unavailable") from None
    except (ValueError, KeyError, TypeError, IndexError, UnicodeError):
        raise HTTPException(502, "Invalid local model response") from None
    return JSONResponse({"response": text}, headers={"Cache-Control": "no-store"})
