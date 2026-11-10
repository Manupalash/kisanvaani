"""Async adapter for Gnani Timbre v2.5 speech synthesis."""

import asyncio
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import random
import re
import time

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger("kisanvaani.gnani_tts")
MODEL_V25 = "timbre-v2.5"
TE_TELUGU_VOICES = {"Suhana", "Lehara", "Lavanya", "Yukti", "Varuni"}
ENGLISH_VOICES = {"Kaveri", "Trupti", "Devika", "Pranav", "Shlok", "Girish"}
SUPPORTED_LANGUAGES = {"te-IN", "en-IN", "auto"}
MAX_RETRIES = 2


@dataclass(frozen=True)
class SynthesizedAudio:
    content: bytes
    media_type: str
    model: str
    language: str
    voice: str
    upstream_status: int


def _mime_from_response(content_type: str, content: bytes) -> str:
    media_type = content_type.split(";", 1)[0].strip().lower()
    signatures = {
        "audio/wav": content.startswith(b"RIFF") and content[8:12] == b"WAVE",
        "audio/x-wav": content.startswith(b"RIFF") and content[8:12] == b"WAVE",
        "audio/mpeg": content.startswith(b"ID3") or (len(content) > 1 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0),
        "audio/ogg": content.startswith(b"OggS"),
    }
    if media_type in signatures and signatures[media_type]:
        return media_type
    if media_type in {"application/octet-stream", "binary/octet-stream"}:
        for candidate, valid in signatures.items():
            if valid:
                return candidate
    raise HTTPException(status_code=502, detail="Gnani returned an unsupported or invalid audio response. Please retry.")


def _normalize_wav_sizes(content: bytes) -> bytes:
    """Repair the common streaming-WAV all-ones size markers for browser playback."""
    if len(content) < 44 or content[:4] != b"RIFF" or content[8:12] != b"WAVE":
        return content
    output = bytearray(content)
    riff_size = struct.unpack_from("<I", output, 4)[0]
    data_offset = output.find(b"data", 12)
    if data_offset < 0 or data_offset + 8 > len(output):
        return content
    data_size_offset = data_offset + 4
    data_size = struct.unpack_from("<I", output, data_size_offset)[0]
    if riff_size == 0xFFFFFFFF:
        struct.pack_into("<I", output, 4, len(output) - 8)
    if data_size == 0xFFFFFFFF:
        struct.pack_into("<I", output, data_size_offset, len(output) - (data_offset + 8))
    return bytes(output)


class TimbreTTSService:
    """Uses the same backend-only GNANI_API_KEY as Prisma STT."""

    def __init__(self, api_key: str | None = None, endpoint: str | None = None, timeout: float | None = None, client_factory=None):
        self.api_key = api_key if api_key is not None else settings.gnani_api_key
        self.endpoint = endpoint or settings.gnani_tts_url
        self.timeout = timeout if timeout is not None else settings.gnani_tts_timeout_seconds
        self.client_factory = client_factory or httpx.AsyncClient

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    @staticmethod
    def _safe_error_code(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return "non_json_error"
        if not isinstance(payload, dict):
            return "unstructured_error"
        detail = payload.get("detail")
        if isinstance(detail, dict):
            code = detail.get("error_code") or detail.get("type")
        else:
            error = payload.get("error")
            code = error.get("type") if isinstance(error, dict) else None
        if not isinstance(code, str):
            code = "provider_error"
        return re.sub(r"[^A-Za-z0-9_-]", "", code)[:64] or "provider_error"

    @staticmethod
    def _choose_voice(language: str, voice: str | None) -> str:
        if language == "en-IN":
            allowed, default = ENGLISH_VOICES, settings.gnani_tts_english_voice
        elif language == "te-IN":
            allowed, default = TE_TELUGU_VOICES, settings.gnani_tts_telugu_voice
        else:  # Timbre documents `auto` for script-based detection; Telugu voice is default for mixed Telugu-English.
            allowed = TE_TELUGU_VOICES | ENGLISH_VOICES
            default = settings.gnani_tts_telugu_voice
        selected = voice or default
        if selected not in allowed:
            raise HTTPException(status_code=422, detail="The requested voice is not supported for this language and Timbre model.")
        return selected

    @staticmethod
    def _failure(status: int | None) -> HTTPException:
        if status in {401, 403}:
            return HTTPException(status_code=502, detail="Gnani TTS credentials lack authentication or service access. Confirm the configured Gnani key has TTS permission.")
        if status == 402:
            return HTTPException(status_code=503, detail="Gnani TTS credits are unavailable. Check the Gnani account and retry later.")
        if status == 429:
            return HTTPException(status_code=503, detail="Gnani TTS is rate-limited. Your text answer is still available; retry audio shortly.")
        if status == 400:
            return HTTPException(status_code=502, detail="Gnani rejected the TTS model, voice, language, or audio configuration. Check backend TTS settings.")
        if status in {500, 502, 503, 504}:
            return HTTPException(status_code=503, detail="Gnani TTS is temporarily unavailable. Your text answer is still available; retry audio shortly.")
        if status is None:
            return HTTPException(status_code=503, detail="Could not reach Gnani TTS. Your text answer is still available; retry audio shortly.")
        return HTTPException(status_code=502, detail="Gnani TTS could not generate audio. Your text answer is still available.")

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> SynthesizedAudio:
        clean_text = text.strip()
        if not clean_text:
            raise HTTPException(status_code=422, detail="Text must not be empty.")
        if len(clean_text) > settings.gnani_tts_max_text_chars:
            raise HTTPException(status_code=413, detail=f"Text exceeds the {settings.gnani_tts_max_text_chars} character speech limit.")
        if language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=422, detail="Language must be te-IN, en-IN, or auto for documented mixed-language detection.")
        if not self.api_key:
            raise HTTPException(status_code=503, detail="Gnani TTS is not configured. Set the existing GNANI_API_KEY in backend/.env.")
        model = settings.gnani_tts_model
        if model != MODEL_V25:
            raise HTTPException(status_code=503, detail="The configured Gnani TTS model is unsupported. Set GNANI_TTS_MODEL=timbre-v2.5.")
        selected_voice = self._choose_voice(language, voice)
        payload = {
            "text": clean_text,
            "model": model,
            "language": language,
            "voice": selected_voice,
            "audio_config": {
                "encoding": "linear_pcm",
                "container": "wav",
                "num_channels": 1,
                "sample_rate": 48000,
                "sample_width": 2,
            },
        }
        retries = min(max(settings.gnani_tts_max_retries, 0), MAX_RETRIES)
        started = time.perf_counter()
        response: httpx.Response | None = None
        last_status: int | None = None
        try:
            async with asyncio.timeout(max(0.1, self.timeout)):
                async with self.client_factory(timeout=self.timeout) as client:
                    for attempt in range(retries + 1):
                        try:
                            response = await client.post(
                                self.endpoint,
                                headers={"X-API-Key-ID": self.api_key},
                                json=payload,
                            )
                        except (httpx.TimeoutException, httpx.RequestError) as exc:
                            logger.warning(
                                "tts_request_failed attempt=%s max_attempts=%s upstream_status=none exception_class=%s error_category=%s",
                                attempt + 1, retries + 1, type(exc).__name__, "timeout" if isinstance(exc, httpx.TimeoutException) else "network",
                            )
                            if attempt >= retries:
                                raise self._failure(None) from exc
                            base = min(4.0, 0.5 * 2**attempt)
                            await asyncio.sleep(random.uniform(base * 0.5, base))
                            continue
                        last_status = response.status_code
                        if response.is_success:
                            break
                        error_code = self._safe_error_code(response)
                        logger.warning(
                            "tts_upstream_error attempt=%s max_attempts=%s upstream_status=%s error_code=%s",
                            attempt + 1, retries + 1, last_status, error_code,
                        )
                        retryable = last_status in {429, 500, 502, 503, 504}
                        if not retryable or attempt >= retries:
                            raise self._failure(last_status)
                        base = min(4.0, 0.5 * 2**attempt)
                        delay = random.uniform(base * 0.5, base)
                        retry_after = self._retry_after(response)
                        if retry_after is not None:
                            delay = max(delay, retry_after)
                        await asyncio.sleep(delay)
        except TimeoutError as exc:
            logger.warning("tts_overall_timeout timeout_seconds=%.2f model=%s language=%s", self.timeout, model, language)
            raise HTTPException(status_code=504, detail="Gnani TTS timed out. Your text answer is still available; retry audio.") from exc

        elapsed = round(time.perf_counter() - started, 3)
        if response is None or not response.is_success:
            raise self._failure(last_status)
        content = response.content
        media_type = _mime_from_response(response.headers.get("Content-Type", ""), content)
        if media_type in {"audio/wav", "audio/x-wav"}:
            content = _normalize_wav_sizes(content)
        logger.info(
            "tts_audio_ready upstream_status=%s duration_seconds=%s audio_bytes=%s media_type=%s model=%s language=%s voice=%s",
            response.status_code, elapsed, len(content), media_type, model, language, selected_voice,
        )
        return SynthesizedAudio(content, media_type, model, language, selected_voice, response.status_code)
