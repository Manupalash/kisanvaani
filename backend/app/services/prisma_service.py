import os
import json
import logging
import re
import time
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.services.audio_service import PreparedAudio

logger = logging.getLogger("kisanvaani.prisma")
_SECRET_PATTERN = re.compile(r"(?i)(api[_ -]?key|authorization|token|secret)([\"']?\s*[:=]\s*[\"']?)([^\s,\"'}]+)")


def _safe_body(response: httpx.Response, api_key: str) -> str:
    try:
        body = response.json()
    except ValueError:
        body = response.text[:1200]

    def sanitize(value: Any, key: str = "") -> Any:
        if any(token in key.lower() for token in ("transcript", "text", "audio", "content", "payload", "data", "utterance")):
            return "[REDACTED]"
        if key.lower() == "error":
            return "[REDACTED: upstream error detail]"
        if isinstance(value, dict):
            # Error bodies can echo input. Keep only diagnostic identifiers, never free-form detail.
            return {str(k): sanitize(v, str(k)) for k, v in list(value.items())[:20]
                    if any(term in str(k).lower() for term in ("code", "type", "status", "error"))}
        if isinstance(value, list):
            return [sanitize(item) for item in value[:20]]
        if isinstance(value, str):
            value = value.replace(api_key, "[REDACTED]")
            value = _SECRET_PATTERN.sub(r"\1\2[REDACTED]", value)
            return value[:500]
        return value

    if isinstance(body, str):
        body = {"body": "[REDACTED: non-JSON upstream body]", "length": len(body)}
    return json.dumps(sanitize(body), ensure_ascii=False, separators=(",", ":"))[:1200]


def _log(event: str, **fields: Any) -> None:
    logger.info("%s", json.dumps({"event": event, **fields}, ensure_ascii=False, separators=(",", ":")))


class PrismaService:
    def __init__(self, api_key: str | None = None, endpoint: str | None = None, timeout: float | None = None):
        self.api_key = api_key if api_key is not None else (settings.gnani_api_key or os.getenv("GNANI_API_KEY"))
        self.endpoint = endpoint or settings.gnani_stt_url
        self.timeout = timeout or settings.gnani_timeout_seconds

    async def transcribe(self, audio: PreparedAudio, language: str = "te-IN") -> dict[str, Any]:
        if not self.api_key:
            raise HTTPException(status_code=503, detail="Speech transcription is not configured. Set GNANI_API_KEY on the backend.")
        started = time.perf_counter()
        _log("gnani_request_started", endpoint=self.endpoint, audio_mime_type=audio.content_type,
             audio_format=os.path.splitext(audio.filename)[1].lstrip("."), audio_size_bytes=os.path.getsize(audio.path),
             audio_duration_seconds=round(audio.duration, 3), timeout_seconds=self.timeout)
        try:
            with open(audio.path, "rb") as stream:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.endpoint,
                        headers={"X-API-Key-ID": self.api_key},
                        data={"language_code": language},
                        files={"audio_file": (audio.filename, stream, audio.content_type)},
                    )
        except httpx.TimeoutException as exc:
            elapsed = round(time.perf_counter() - started, 3)
            _log("gnani_request_timeout", duration_seconds=elapsed, exception_class=type(exc).__name__,
                 timeout_details=f"configured_timeout={self.timeout}s")
            raise HTTPException(status_code=504, detail=f"Gnani transcription timed out after {self.timeout:g}s. Retry or increase GNANI_TIMEOUT_SECONDS.") from exc
        except httpx.RequestError as exc:
            elapsed = round(time.perf_counter() - started, 3)
            category = "connection_error" if isinstance(exc, httpx.ConnectError) else "upstream_transport_error"
            _log("gnani_request_failed", duration_seconds=elapsed, exception_class=type(exc).__name__, category=category)
            raise HTTPException(status_code=502, detail="Could not connect to Gnani transcription service. Check backend outbound network access and GNANI_STT_URL.") from exc
        elapsed = round(time.perf_counter() - started, 3)
        safe_body = _safe_body(response, self.api_key)
        _log("gnani_response_received", status_code=response.status_code, duration_seconds=elapsed,
             audio_mime_type=audio.content_type, audio_format=os.path.splitext(audio.filename)[1].lstrip("."),
             audio_size_bytes=os.path.getsize(audio.path), response_body=safe_body)
        if response.status_code in (401, 403):
            try:
                error_body = response.json()
                description = " ".join(str(value) for value in error_body.values()).lower() if isinstance(error_body, dict) else ""
            except ValueError:
                description = ""
            if "credit" in description or "balance" in description:
                raise HTTPException(status_code=503, detail="Gnani account has insufficient credits.")
            raise HTTPException(status_code=response.status_code, detail="Gnani authentication failed. Verify GNANI_API_KEY in backend/.env and confirm the key is active.")
        if response.status_code == 402:
            raise HTTPException(status_code=503, detail="Gnani account has insufficient credits.")
        if response.status_code == 429:
            raise HTTPException(status_code=429, detail="Gnani rate limit reached. Please wait and retry.")
        if response.status_code == 404:
            raise HTTPException(status_code=502, detail="Gnani STT endpoint was not found. Verify GNANI_STT_URL is https://api.vachana.ai/stt/v3.")
        if response.status_code == 422:
            raise HTTPException(status_code=422, detail="Gnani could not process this audio request. Check that the audio format is supported and language is te-IN.")
        if response.status_code >= 500:
            raise HTTPException(status_code=502, detail=f"Gnani transcription service returned HTTP {response.status_code}. Retry later; see backend diagnostics for the sanitized response.")
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=f"Gnani rejected the request with HTTP {response.status_code}. Check the audio format and language_code.")
        try:
            payload = response.json()
        except ValueError as exc:
            _log("gnani_malformed_json", status_code=response.status_code, duration_seconds=elapsed,
                 exception_class=type(exc).__name__, response_body=safe_body)
            raise HTTPException(status_code=502, detail="Gnani returned malformed JSON. Retry; if persistent, inspect sanitized backend diagnostics.") from exc
        if not isinstance(payload, dict) or payload.get("success") is not True or not isinstance(payload.get("transcript"), str):
            _log("gnani_invalid_response", status_code=response.status_code, duration_seconds=elapsed,
                 exception_class="InvalidResponseShape", response_body=safe_body)
            raise HTTPException(status_code=502, detail="Gnani returned an invalid transcription response. Inspect sanitized backend diagnostics.")
        return {
            "success": True,
            "transcript": payload["transcript"],
            "model": payload.get("model") if isinstance(payload.get("model"), str) else "prisma-v2.5",
            "request_id": payload.get("request_id") if isinstance(payload.get("request_id"), str) else None,
            "language": language,
        }
