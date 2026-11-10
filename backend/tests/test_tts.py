import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app import models  # noqa: F401
from app.services.tts_service import TimbreTTSService


def wav_fixture():
    # Minimal valid-looking WAV payload; route checks audio signature, not decoding.
    return b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt " + (16).to_bytes(4, "little") + b"\x01\x00\x01\x00" + (48000).to_bytes(4, "little") + (96000).to_bytes(4, "little") + b"\x02\x00\x10\x00data" + (0).to_bytes(4, "little")


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "gnani_api_key", "test-key")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_tts_endpoint_sends_documented_request_and_returns_audio(client, monkeypatch):
    captured = {}

    class Client:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, headers, json):
            captured.update(url=url, headers=headers, json=json)
            return httpx.Response(200, content=wav_fixture(), headers={"Content-Type": "audio/wav"})

    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    response = client.post("/api/v1/voice/synthesize", json={"text": "నమస్కారం", "language": "te-IN"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.headers["cache-control"] == "no-store"
    assert captured["url"] == "https://api.vachana.ai/api/v1/tts/inference"
    assert captured["headers"] == {"X-API-Key-ID": "test-key"}
    assert captured["json"] == {
        "text": "నమస్కారం", "model": "timbre-v2.5", "language": "te-IN", "voice": "Yukti",
        "audio_config": {"encoding": "linear_pcm", "container": "wav", "num_channels": 1, "sample_rate": 48000, "sample_width": 2},
    }


def test_streaming_wav_unknown_lengths_are_normalized_for_browser_playback(monkeypatch):
    raw = bytearray(b"RIFF" + (0xFFFFFFFF).to_bytes(4, "little") + b"WAVEfmt " + (16).to_bytes(4, "little") + b"\x01\x00\x01\x00" + (48000).to_bytes(4, "little") + (96000).to_bytes(4, "little") + b"\x02\x00\x10\x00data" + (0xFFFFFFFF).to_bytes(4, "little") + b"\x00\x00" * 960)

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return httpx.Response(200, content=bytes(raw), headers={"Content-Type": "audio/wav"})

    monkeypatch.setattr("app.services.tts_service.settings.gnani_api_key", "key")
    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    result = asyncio.run(TimbreTTSService().synthesize("hello", "en-IN"))
    import struct
    assert struct.unpack_from("<I", result.content, 4)[0] == len(raw) - 8
    assert struct.unpack_from("<I", result.content, 40)[0] == len(raw) - 44
    import wave
    import io
    with wave.open(io.BytesIO(result.content), "rb") as wav:
        assert wav.getnframes() == 960


def test_english_voice_and_mixed_language(client, monkeypatch):
    captured = []

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers, json):
            captured.append(json)
            return httpx.Response(200, content=wav_fixture(), headers={"Content-Type": "audio/wav"})

    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    assert client.post("/api/v1/voice/synthesize", json={"text": "Hello farmer", "language": "en-IN"}).status_code == 200
    assert client.post("/api/v1/voice/synthesize", json={"text": "పంట check చేయండి", "language": "auto"}).status_code == 200
    assert captured[0]["voice"] == "Shlok"
    assert captured[1]["language"] == "auto"


def test_tts_uses_configured_default_language(client, monkeypatch):
    captured = {}

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers, json):
            captured.update(json)
            return httpx.Response(200, content=wav_fixture(), headers={"Content-Type": "audio/wav"})

    monkeypatch.setattr(settings, "gnani_tts_default_language", "en-IN")
    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    response = client.post("/api/v1/voice/synthesize", json={"text": "Hello farmer"})
    assert response.status_code == 200
    assert captured["language"] == "en-IN"
    assert captured["voice"] == "Shlok"


@pytest.mark.parametrize("payload", [{"text": "", "language": "te-IN"}, {"text": "Hello", "language": "fr-FR"}, {"text": "hello", "language": "en-IN", "voice": "Unknown"}])
def test_invalid_tts_input_is_rejected(client, payload):
    assert client.post("/api/v1/voice/synthesize", json=payload).status_code == 422


@pytest.mark.parametrize("status,expected", [(401, 502), (403, 502), (400, 502), (402, 503)])
def test_provider_permanent_errors_are_mapped_safely(client, monkeypatch, status, expected):
    calls = 0

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            return httpx.Response(status, json={"detail": "sensitive provider text"})

    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    response = client.post("/api/v1/voice/synthesize", json={"text": "hello", "language": "en-IN"})
    assert response.status_code == expected
    assert "sensitive provider text" not in response.text
    assert calls == 1


def test_missing_key_and_bad_audio_response(client, monkeypatch):
    monkeypatch.setattr(settings, "gnani_api_key", "")
    assert client.post("/api/v1/voice/synthesize", json={"text": "hello", "language": "en-IN"}).status_code == 503
    monkeypatch.setattr(settings, "gnani_api_key", "test-key")

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return httpx.Response(200, content=b"not audio", headers={"Content-Type": "audio/wav"})

    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    assert client.post("/api/v1/voice/synthesize", json={"text": "hello", "language": "en-IN"}).status_code == 502


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_transient_status_retries_then_succeeds(monkeypatch, status):
    calls, sleeps = [], []

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                return httpx.Response(status, json={"error": {"type": "temporary"}}, headers={"Retry-After": "0"})
            return httpx.Response(200, content=wav_fixture(), headers={"Content-Type": "audio/wav"})

    async def no_sleep(seconds): sleeps.append(seconds)
    monkeypatch.setattr("app.services.tts_service.settings.gnani_api_key", "key")
    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.services.tts_service.asyncio.sleep", no_sleep)
    audio = asyncio.run(TimbreTTSService().synthesize("hello", "en-IN"))
    assert audio.content.startswith(b"RIFF")
    assert len(calls) == 2
    assert len(sleeps) == 1


def test_exhausted_retries_and_network_error_are_bounded(monkeypatch):
    calls, sleeps = [], []

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            calls.append(1)
            return httpx.Response(503, json={"detail": "unavailable"})

    async def no_sleep(seconds): sleeps.append(seconds)
    monkeypatch.setattr("app.services.tts_service.settings.gnani_api_key", "key")
    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.services.tts_service.asyncio.sleep", no_sleep)
    with pytest.raises(Exception) as failure:
        asyncio.run(TimbreTTSService().synthesize("hello", "en-IN"))
    assert failure.value.status_code == 503
    assert len(calls) == 3
    assert len(sleeps) == 2


def test_retry_after_header_is_respected(monkeypatch):
    delays = []
    calls = 0

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(429, headers={"Retry-After": "1.25"})
            return httpx.Response(200, content=wav_fixture(), headers={"Content-Type": "audio/wav"})

    async def no_sleep(seconds): delays.append(seconds)
    monkeypatch.setattr("app.services.tts_service.settings.gnani_api_key", "key")
    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.services.tts_service.asyncio.sleep", no_sleep)
    asyncio.run(TimbreTTSService().synthesize("hello", "en-IN"))
    assert delays == [1.25]


def test_network_failure_retries_bounded_without_logging_key(monkeypatch, caplog):
    calls, sleeps = [], []

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            calls.append(1)
            raise httpx.ConnectError("private connection detail")

    async def no_sleep(seconds): sleeps.append(seconds)
    monkeypatch.setattr("app.services.tts_service.settings.gnani_api_key", "must-not-log-key")
    monkeypatch.setattr("app.services.tts_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.services.tts_service.asyncio.sleep", no_sleep)
    with pytest.raises(Exception) as failure:
        asyncio.run(TimbreTTSService().synthesize("hello", "en-IN"))
    assert failure.value.status_code == 503
    assert len(calls) == 3 and len(sleeps) == 2
    assert "must-not-log-key" not in caplog.text
    assert "private connection detail" not in caplog.text
