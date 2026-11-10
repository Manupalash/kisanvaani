import io
import os
import sys
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import Base, get_db
from app.main import app
from app import models  # noqa: F401
from app.services.audio_service import prepare_audio
from app.services.prisma_service import PrismaService


def wav_bytes(seconds=1):
    result = io.BytesIO()
    with wave.open(result, "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 16000 * seconds)
    return result.getvalue()


def wav_bytes_millis(milliseconds):
    result = io.BytesIO()
    with wave.open(result, "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(b"\0\0" * (16000 * milliseconds // 1000))
    return result.getvalue()


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    def override_db():
        db = testing_session()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client: yield test_client
    app.dependency_overrides.clear(); Base.metadata.drop_all(bind=engine); engine.dispose()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/v1/health").status_code == 200


def test_success_request_header_fields_and_persistence(client, monkeypatch):
    captured = {}
    class Client:
        def __init__(self, timeout): captured["timeout"] = timeout
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers, data, files):
            captured.update(url=url, headers=headers, data=data, files=files)
            return httpx.Response(200, json={"success": True, "transcript": "వరి పంటకు నీరు ఇవ్వండి", "request_id": "req-1", "model": "prisma-v2.5"})
    monkeypatch.setattr("app.services.prisma_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.services.prisma_service.settings.gnani_api_key", "test-secret")
    farmer = client.post("/api/v1/farmers/", json={"name": "Demo"}).json()
    conv = client.post(f"/api/v1/farmers/{farmer['id']}/conversations", json={"title": "Question"}).json()
    response = client.post("/api/v1/voice/transcribe", data={"language": "te-IN", "farmer_id": str(farmer["id"]), "conversation_id": str(conv["id"])}, files={"audio": ("recording.wav", wav_bytes(), "audio/wav")})
    assert response.status_code == 200, response.text
    assert response.json() == {"success": True, "transcript": "వరి పంటకు నీరు ఇవ్వండి", "model": "prisma-v2.5", "request_id": "req-1", "language": "te-IN"}
    assert captured["url"] == "https://api.vachana.ai/stt/v3"
    assert captured["headers"] == {"X-API-Key-ID": "test-secret"}
    assert captured["data"] == {"language_code": "te-IN"}
    assert "model" not in captured["data"]
    assert client.get(f"/api/v1/conversations/{conv['id']}/messages").json()[0]["text"] == response.json()["transcript"]


@pytest.mark.parametrize("status,expected", [(401, 401), (403, 403), (404, 502), (422, 422), (429, 429), (402, 503), (500, 502), (503, 502)])
def test_upstream_status_errors(status, expected, tmp_path):
    audio = tmp_path / "sample.wav"; audio.write_bytes(wav_bytes())
    from app.services.audio_service import PreparedAudio
    prepared = PreparedAudio(str(audio), "x.wav", "audio/wav", 1)
    async def mock_post(*args, **kwargs): return httpx.Response(status, json={"detail": "upstream rejected request"})
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        post = mock_post
    with patch("app.services.prisma_service.httpx.AsyncClient", Client):
        with pytest.raises(Exception) as exc: asyncio_run(PrismaService("secret").transcribe(prepared))
    assert getattr(exc.value, "status_code", None) == expected


def test_insufficient_credits_from_forbidden_response(tmp_path):
    from app.services.audio_service import PreparedAudio
    audio = tmp_path / "sample.wav"; audio.write_bytes(wav_bytes())
    prepared = PreparedAudio(str(audio), "x.wav", "audio/wav", 1)
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return httpx.Response(403, json={"error": "Insufficient credits"})
    with patch("app.services.prisma_service.httpx.AsyncClient", Client):
        with pytest.raises(Exception) as error: asyncio_run(PrismaService("secret").transcribe(prepared))
    assert getattr(error.value, "status_code", None) == 503


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


def test_missing_key_and_timeout(tmp_path):
    from app.services.audio_service import PreparedAudio
    audio = tmp_path / "sample.wav"; audio.write_bytes(wav_bytes())
    prepared = PreparedAudio(str(audio), "x.wav", "audio/wav", 1)
    with pytest.raises(Exception) as missing: asyncio_run(PrismaService("").transcribe(prepared))
    assert getattr(missing.value, "status_code", None) == 503
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): raise httpx.TimeoutException("timeout")
    with patch("app.services.prisma_service.httpx.AsyncClient", Client):
        with pytest.raises(Exception) as timeout: asyncio_run(PrismaService("secret").transcribe(prepared))
    assert getattr(timeout.value, "status_code", None) == 504


def test_malformed_response(tmp_path):
    from app.services.audio_service import PreparedAudio
    audio = tmp_path / "sample.wav"; audio.write_bytes(wav_bytes())
    prepared = PreparedAudio(str(audio), "x.wav", "audio/wav", 1)
    class Response:
        status_code = 200
        text = "not-json"
        def json(self): raise ValueError("bad json")
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return Response()
    with patch("app.services.prisma_service.httpx.AsyncClient", Client):
        with pytest.raises(Exception) as error: asyncio_run(PrismaService("secret").transcribe(prepared))
    assert getattr(error.value, "status_code", None) == 502


def test_connection_error_is_distinct_and_logs_no_secret(tmp_path, caplog):
    caplog.set_level("INFO", logger="kisanvaani.prisma")
    from app.services.audio_service import PreparedAudio
    audio = tmp_path / "sample.wav"; audio.write_bytes(wav_bytes())
    prepared = PreparedAudio(str(audio), "x.wav", "audio/wav", 1)
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): raise httpx.ConnectError("network unavailable")
    with patch("app.services.prisma_service.httpx.AsyncClient", Client):
        with pytest.raises(Exception) as error: asyncio_run(PrismaService("never-log-this-key").transcribe(prepared))
    assert getattr(error.value, "status_code", None) == 502
    assert "connection_error" in caplog.text
    assert "never-log-this-key" not in caplog.text


def test_response_logs_exclude_audio_text_and_credentials():
    from app.services.prisma_service import _safe_body
    response = httpx.Response(400, json={"code": "BAD_AUDIO", "transcript": "private speech", "detail": "private speech", "audio": "private audio"})
    body = _safe_body(response, "secret-key")
    assert "BAD_AUDIO" in body
    assert "private speech" not in body and "private audio" not in body and "secret-key" not in body


def test_upload_rejects_invalid_unsupported_oversize_and_duration(client, monkeypatch):
    assert client.post("/api/v1/voice/transcribe", files={"audio": ("bad.wav", b"not audio", "audio/wav")}).status_code == 400
    assert client.post("/api/v1/voice/transcribe", files={"audio": ("bad.xyz", b"data", "application/octet-stream")}).status_code == 415
    assert client.post("/api/v1/voice/transcribe", files={"audio": ("large.wav", b"x"*(10*1024*1024+1), "audio/wav")}).status_code == 413
    long_wav = wav_bytes(31)
    assert client.post("/api/v1/voice/transcribe", files={"audio": ("long.wav", long_wav, "audio/wav")}).status_code == 413


@pytest.mark.parametrize("milliseconds", [300, 800, 1000, 15000])
def test_audio_duration_boundaries(client, monkeypatch, milliseconds):
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return httpx.Response(200, json={"success": True, "transcript": "నమస్కారం", "model": "prisma-v2.5"})
    monkeypatch.setattr("app.services.prisma_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.services.prisma_service.settings.gnani_api_key", "mock-key")
    audio = wav_bytes_millis(milliseconds)
    duration = milliseconds / 1000
    response = client.post("/api/v1/voice/transcribe", data={"duration_seconds": f"{duration:.3f}"}, files={"audio": ("sample.wav", audio, "audio/wav")})
    assert response.status_code == 200, response.text


def test_missing_duration_metadata_uses_server_measurement(client, monkeypatch):
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return httpx.Response(200, json={"success": True, "transcript": "నమస్కారం"})
    monkeypatch.setattr("app.services.prisma_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.services.prisma_service.settings.gnani_api_key", "mock-key")
    response = client.post("/api/v1/voice/transcribe", files={"audio": ("sample.wav", wav_bytes_millis(300), "audio/wav")})
    assert response.status_code == 200, response.text


def test_zero_and_incorrect_client_duration_are_handled(client, monkeypatch):
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return httpx.Response(200, json={"success": True, "transcript": "test"})
    monkeypatch.setattr("app.services.prisma_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("app.services.prisma_service.settings.gnani_api_key", "mock-key")
    zero = client.post("/api/v1/voice/transcribe", data={"duration_seconds": "0"}, files={"audio": ("sample.wav", wav_bytes_millis(300), "audio/wav")})
    assert zero.status_code == 200
    wrong = client.post("/api/v1/voice/transcribe", data={"duration_seconds": "12.000"}, files={"audio": ("sample.wav", wav_bytes_millis(300), "audio/wav")})
    assert wrong.status_code == 400


def test_empty_audio_rejected(client):
    response = client.post("/api/v1/voice/transcribe", files={"audio": ("empty.wav", b"", "audio/wav")})
    assert response.status_code == 400


def test_zero_duration_recording_rejected(client):
    response = client.post("/api/v1/voice/transcribe", files={"audio": ("zero.wav", wav_bytes_millis(0), "audio/wav")})
    assert response.status_code == 400


def test_missing_credentials_route_returns_clear_error(client, monkeypatch):
    monkeypatch.setattr("app.services.prisma_service.settings.gnani_api_key", None)
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    response = client.post("/api/v1/voice/transcribe", files={"audio": ("sample.wav", wav_bytes(), "audio/wav")})
    assert response.status_code == 503
    assert "GNANI_API_KEY" in response.json()["detail"]


def test_webm_ffmpeg_conversion():
    import shutil
    import subprocess
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg: pytest.skip("FFmpeg not installed")
    with tempfile.TemporaryDirectory() as folder:
        source = os.path.join(folder, "source.wav")
        webm = os.path.join(folder, "sample.webm")
        with open(source, "wb") as f: f.write(wav_bytes())
        subprocess.run([ffmpeg, "-v", "error", "-i", source, "-c:a", "libopus", webm], check=True)
        class Upload:
            filename = "recording.webm"; content_type = "audio/webm"
            def __init__(self): self.file = open(webm, "rb")
            async def read(self, size): return self.file.read(size)
        prepared = asyncio_run(prepare_audio(Upload(), ffmpeg_binary=ffmpeg))
        try:
            assert prepared.content_type == "audio/wav"
            with wave.open(prepared.path, "rb") as output:
                assert output.getnchannels() == 1 and output.getframerate() == 16000 and output.getsampwidth() == 2
        finally: prepared.cleanup()
