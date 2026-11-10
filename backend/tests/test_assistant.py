import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: F401
from app.db.session import Base, get_db
from app.main import app
from app.models import AgriculturalDocument, Conversation, Farmer, FarmCrop, Message
from app.services.knowledge_service import retrieve_documents, seed_knowledge_base
from app.services.reasoning_provider import get_reasoning_provider


class StubProvider:
    def __init__(self, answer="The soil condition is not enough to identify the cause."):
        self.answer_text = answer
        self.last_context = None

    async def answer(self, **kwargs):
        self.last_context = kwargs
        return self.answer_text


@pytest.fixture()
def app_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as session:
        farmer = Farmer(name="Ramu", village="Chandur", district="Nalgonda")
        session.add(farmer); session.commit(); session.refresh(farmer)
        crop = FarmCrop(farmer_id=farmer.id, name="వరి Paddy", stage="Tillering", area_acres=2)
        conversation = Conversation(farmer_id=farmer.id, title="Paddy question")
        session.add_all([crop, conversation]); session.commit(); session.refresh(conversation)
        seed_knowledge_base(session)
        ids = farmer.id, conversation.id
    def override_db():
        db = TestingSession()
        try: yield db
        finally: db.close()
    provider = StubProvider()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_reasoning_provider] = lambda: provider
    with TestClient(app, raise_server_exceptions=False) as client:
        client.test_ids = ids
        client.test_provider = provider
        yield client
    app.dependency_overrides.clear(); Base.metadata.drop_all(bind=engine); engine.dispose()


def test_chat_validation_and_owner_check(app_client):
    farmer_id, conversation_id = app_client.test_ids
    assert app_client.post("/api/v1/assistant/chat", json={"farmer_id": farmer_id, "conversation_id": conversation_id, "message": "  "}).status_code == 422
    assert app_client.post("/api/v1/assistant/chat", json={"farmer_id": 999, "conversation_id": conversation_id, "message": "Paddy help"}).status_code == 404
    assert app_client.post("/api/v1/assistant/chat", json={"farmer_id": farmer_id, "conversation_id": 999, "message": "Paddy help"}).status_code == 404


def test_retrieval_relevance_source_attribution_and_persistence(app_client):
    farmer_id, conversation_id = app_client.test_ids
    db = next(app.dependency_overrides[get_db]())
    try:
        results = retrieve_documents(db, "paddy irrigation water", ["వరి Paddy"])
        assert results
        assert "water" in results[0].title.lower()
        assert results[0].source_name and results[0].source_url.startswith("https://")
    finally: db.close()
    response = app_client.post("/api/v1/assistant/chat", json={"farmer_id": farmer_id, "conversation_id": conversation_id, "message": "వరి పంటకు water ఎలా manage చేయాలి?"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["language"] == "te-en"
    assert payload["conversation_id"] == conversation_id
    assert payload["retrieved_sources"] and payload["retrieved_sources"][0]["source_url"].startswith("https://")
    assert app_client.test_provider.last_context["farmer_context"].find("Paddy") >= 0
    messages = app_client.get(f"/api/v1/conversations/{conversation_id}/messages").json()
    assert [message["role"] for message in messages] == ["user", "assistant"]


@pytest.mark.parametrize("message,language", [("వరి ఆకులు పసుపు", "te"), ("My paddy leaves are yellow", "en"), ("వరి leaves yellow అవుతున్నాయి", "te-en")])
def test_language_detection(app_client, message, language):
    from app.api.v1.routes.assistant import detect_language
    assert detect_language(message) == language


def test_missing_agricultural_context_returns_retrieval_empty(app_client):
    db = next(app.dependency_overrides[get_db]())
    try:
        assert retrieve_documents(db, "unrelated quantum question") == []
    finally: db.close()


@pytest.mark.parametrize("unsafe", ["Spray 2 ml per litre for confirmed blast.", "Apply 5 g per acre; definitely borer."])
def test_safety_guard_blocks_dosages_and_definitive_diagnosis(app_client, unsafe):
    from app.api.v1.routes.assistant import validate_answer_safety
    safe = validate_answer_safety(unsafe, "en")
    assert safe != unsafe
    assert "dose" in safe.lower() or "diagnosis" in safe.lower()


def test_provider_failure_does_not_persist_messages(app_client):
    farmer_id, conversation_id = app_client.test_ids
    class BrokenProvider:
        async def answer(self, **kwargs): raise RuntimeError("provider offline")
    app.dependency_overrides[get_reasoning_provider] = lambda: BrokenProvider()
    try:
        response = app_client.post("/api/v1/assistant/chat", json={"farmer_id": farmer_id, "conversation_id": conversation_id, "message": "Paddy question"})
        assert response.status_code == 502
        assert app_client.get(f"/api/v1/conversations/{conversation_id}/messages").json() == []
    finally:
        app.dependency_overrides[get_reasoning_provider] = lambda: app_client.test_provider


def test_retrieval_covers_six_crops_and_telugu_topics(app_client):
    db = next(app.dependency_overrides[get_db]())
    try:
        expected = {
            "వరి నీరు ఎప్పుడు ఇవ్వాలి": "rice",
            "పత్తి తెగులు": "cotton",
            "మిరప ఆకుల వ్యాధి": "chilli",
            "మొక్కజొన్న harvest": "maize",
            "వేరుశనగ కోత ఎప్పుడు": "groundnut",
            "టమాటా పురుగు": "tomato",
        }
        for query, crop in expected.items():
            docs = retrieve_documents(db, query)
            assert docs, query
            assert any(crop in (doc.crop or "").lower() for doc in docs), query
        assert all(doc.source_url and doc.source_name and doc.content for doc in retrieve_documents(db, "rice irrigation water"))
    finally:
        db.close()


def test_retrieval_favors_explicit_crop_over_profile_context(app_client):
    db = next(app.dependency_overrides[get_db]())
    try:
        docs = retrieve_documents(db, "tomato fruit borer", ["వరి Paddy"])
        assert docs
        assert "tomato" in (docs[0].crop or "").lower()
    finally:
        db.close()


def test_openai_provider_uses_documented_request_and_handles_errors(monkeypatch):
    import asyncio
    import httpx
    from fastapi import HTTPException
    from app.services.reasoning_provider import OPENAI_CHAT_COMPLETIONS_URL, OpenAIChatProvider

    captured = {}
    class FakeResponse:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": "Ask the farmer for the crop stage."}}]}
    class FakeClient:
        def __init__(self, timeout): captured["timeout"] = timeout
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, json=json)
            return FakeResponse()
    monkeypatch.setattr("app.services.reasoning_provider.httpx.AsyncClient", FakeClient)
    provider = OpenAIChatProvider(api_key="test-key", model="test-model", timeout=12)
    result = asyncio.run(provider.answer(question="My tomato leaves are curling", farmer_context="Tomato field", sources=[], history=[]))
    assert result.startswith("Ask the farmer")
    assert captured["url"] == OPENAI_CHAT_COMPLETIONS_URL
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "test-model"
    assert "No matching verified source" in captured["json"]["messages"][-1]["content"]
    assert captured["timeout"] == 12

    class RateLimitedResponse(FakeResponse): status_code = 429
    class RateLimitedClient(FakeClient):
        async def post(self, *args, **kwargs): return RateLimitedResponse()
    monkeypatch.setattr("app.services.reasoning_provider.httpx.AsyncClient", RateLimitedClient)
    with pytest.raises(HTTPException) as error:
        asyncio.run(provider.answer(question="Question", farmer_context="", sources=[], history=[]))
    assert error.value.status_code == 503


def test_provider_missing_credentials_fails_closed(monkeypatch):
    from fastapi import HTTPException
    from app.services.reasoning_provider import OpenAIChatProvider
    import asyncio
    with pytest.raises(HTTPException) as error:
        asyncio.run(OpenAIChatProvider(api_key=None, model=None).answer(question="Q", farmer_context="", sources=[], history=[]))
    assert error.value.status_code == 503


@pytest.mark.parametrize("unsafe", [
    "ఖచ్చితంగా ఇది వైరస్.",
    "Mix pesticide A with fungicide B and spray it.",
    "పురుగుమందు మోతాదు 2 ml ఒక లీటరుకు వాడండి.",
])
def test_safety_guard_covers_telugu_diagnosis_and_chemical_mixing(unsafe):
    from app.api.v1.routes.assistant import validate_answer_safety
    language = "te" if any("\u0c00" <= char <= "\u0c7f" for char in unsafe) else "en"
    safe = validate_answer_safety(unsafe, language)
    assert safe != unsafe


def test_gemini_provider_initialization_and_factory(monkeypatch):
    from app.core.config import settings
    from app.services.reasoning_provider import GeminiProvider

    monkeypatch.setattr(settings, "assistant_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "sdk-test-secret")
    monkeypatch.setattr(settings, "gemini_model", "gemini-test-model")
    provider = get_reasoning_provider()
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-test-model"
    assert provider.api_key == "sdk-test-secret"


def test_gemini_success_prompt_context_and_low_latency_config(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from app.services.knowledge_service import RetrievedSource
    from app.services.reasoning_provider import GeminiProvider

    captured = {}
    class FakeModels:
        async def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="ఈ నీటి వివరాలు ఉపయోగకరంగా ఉన్నాయి.")
    class FakeAio:
        models = FakeModels()
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    client = SimpleNamespace(aio=FakeAio())
    monkeypatch.setattr("app.services.reasoning_provider.genai.Client", lambda **kwargs: (captured.update(client_options=kwargs) or client))
    source = RetrievedSource(1, "Rice water guide", "Keep field water appropriate to crop stage.", "rice", "irrigation", "ICAR-CIWA", "https://example.org/rice", 3)
    answer = asyncio.run(GeminiProvider(api_key="never-log-this", model="gemini-test").answer(
        question="వరి నీరు ఎలా?", farmer_context="Nalgonda; crops: rice", sources=[source],
        history=[{"role": "user", "content": "Earlier question"}],
    ))
    assert answer.startswith("ఈ నీటి")
    assert captured["model"] == "gemini-test"
    prompt = captured["contents"]
    for text in ("వరి నీరు ఎలా?", "Nalgonda", "ICAR-CIWA", "https://example.org/rice", "Earlier question"):
        assert text in prompt
    assert "source URLs" in prompt
    assert captured["config"].thinking_config.thinking_level.value.lower() == "low"
    assert captured["config"].max_output_tokens == 768
    assert captured["client_options"]["api_key"] == "never-log-this"


@pytest.mark.parametrize("question,response", [
    ("How do I prepare soil for rice?", "Use locally recommended field preparation."),
    ("మిరపలో నీరు ఎప్పుడు ఇవ్వాలి?", "మిరప దశను బట్టి నీటి అవసరం మారుతుంది."),
])
def test_gemini_returns_english_and_telugu_responses(monkeypatch, question, response):
    import asyncio
    from types import SimpleNamespace
    from app.services.reasoning_provider import GeminiProvider
    class FakeModels:
        async def generate_content(self, **kwargs): return SimpleNamespace(text=response)
    class FakeAio:
        models = FakeModels()
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    monkeypatch.setattr("app.services.reasoning_provider.genai.Client", lambda **kwargs: SimpleNamespace(aio=FakeAio()))
    assert asyncio.run(GeminiProvider(api_key="test").answer(question=question, farmer_context="", sources=[], history=[])) == response


def test_gemini_missing_key_invalid_key_rate_limit_timeout_and_empty(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.services.reasoning_provider import GeminiProvider

    with pytest.raises(HTTPException) as missing:
        asyncio.run(GeminiProvider(api_key="", model="gemini-test").answer(question="Q", farmer_context="", sources=[], history=[]))
    assert missing.value.status_code == 503

    class FakeAio:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        class models:
            @staticmethod
            async def generate_content(**kwargs): return SimpleNamespace(text="")
    monkeypatch.setattr("app.services.reasoning_provider.genai.Client", lambda **kwargs: SimpleNamespace(aio=FakeAio()))
    with pytest.raises(HTTPException) as empty:
        asyncio.run(GeminiProvider(api_key="test").answer(question="Q", farmer_context="", sources=[], history=[]))
    assert empty.value.status_code == 502 and "empty" in empty.value.detail

    for exception, expected in [
        (type("ClientError", (Exception,), {"code": 403})(), 502),
        (type("ClientError", (Exception,), {"code": 429})(), 503),
        (type("ServerError", (Exception,), {"code": 504})(), 504),
        (TimeoutError("internal timeout details"), 504),
        (type("ConnectError", (Exception,), {})(), 503),
    ]:
        class ErrorAio:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            class models:
                @staticmethod
                async def generate_content(**kwargs): raise exception
        monkeypatch.setattr("app.services.reasoning_provider.genai.Client", lambda **kwargs: SimpleNamespace(aio=ErrorAio()))
        with pytest.raises(HTTPException) as error:
            asyncio.run(GeminiProvider(api_key="test").answer(question="Q", farmer_context="", sources=[], history=[]))
        assert error.value.status_code == expected
        assert "internal timeout details" not in error.value.detail


def test_gemini_safety_block_and_retrieval_only_fallback(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.core.config import settings
    from app.services.reasoning_provider import GeminiProvider

    class FakeAio:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        class models:
            @staticmethod
            async def generate_content(**kwargs):
                return SimpleNamespace(text=None, candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="SAFETY"))])
    monkeypatch.setattr("app.services.reasoning_provider.genai.Client", lambda **kwargs: SimpleNamespace(aio=FakeAio()))
    with pytest.raises(HTTPException) as blocked:
        asyncio.run(GeminiProvider(api_key="test").answer(question="Q", farmer_context="", sources=[], history=[]))
    assert blocked.value.status_code == 422

    monkeypatch.setattr(settings, "assistant_provider", "none")
    with pytest.raises(HTTPException) as retrieval:
        get_reasoning_provider()
    assert retrieval.value.status_code == 503
    assert "Retrieval is available" in retrieval.value.detail


def test_gemini_retries_transient_errors_and_respects_retry_after(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from app.services.reasoning_provider import GeminiProvider

    delays = []
    calls = {"count": 0}
    class ServerError(Exception):
        code = 503
        response = SimpleNamespace(headers={"Retry-After": "2"})
        message = "service unavailable"
    class FakeModels:
        async def generate_content(self, **kwargs):
            calls["count"] += 1
            if calls["count"] < 2:
                raise ServerError()
            return SimpleNamespace(text="Try the question again.")
    class FakeAio:
        models = FakeModels()
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    async def fake_sleep(delay): delays.append(delay)
    monkeypatch.setattr("app.services.reasoning_provider.genai.Client", lambda **kwargs: SimpleNamespace(aio=FakeAio()))
    monkeypatch.setattr("app.services.reasoning_provider.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("app.services.reasoning_provider.random.uniform", lambda low, high: low)
    answer = asyncio.run(GeminiProvider(api_key="test", timeout=10).answer(question="Q", farmer_context="", sources=[], history=[]))
    assert answer == "Try the question again."
    assert calls["count"] == 2
    assert delays == [2.0]


def test_gemini_exhausted_retries_are_bounded_and_return_temporary_unavailability(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.services.reasoning_provider import GeminiProvider, GEMINI_MAX_RETRIES

    calls = {"count": 0}
    delays = []
    class ServerError(Exception):
        code = 503
        message = "unavailable"
    class FakeModels:
        async def generate_content(self, **kwargs):
            calls["count"] += 1
            raise ServerError()
    class FakeAio:
        models = FakeModels()
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    async def fake_sleep(delay): delays.append(delay)
    monkeypatch.setattr("app.services.reasoning_provider.genai.Client", lambda **kwargs: SimpleNamespace(aio=FakeAio()))
    monkeypatch.setattr("app.services.reasoning_provider.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("app.services.reasoning_provider.random.uniform", lambda low, high: low)
    with pytest.raises(HTTPException) as error:
        asyncio.run(GeminiProvider(api_key="test", timeout=10).answer(question="Q", farmer_context="", sources=[], history=[]))
    assert error.value.status_code == 503
    assert "Your question is still here" in error.value.detail
    assert calls["count"] == GEMINI_MAX_RETRIES + 1
    assert len(delays) == GEMINI_MAX_RETRIES


def test_gemini_does_not_retry_auth_or_invalid_request_errors(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.services.reasoning_provider import GeminiProvider

    for status in (400, 401, 403, 422):
        calls = {"count": 0}
        delays = []
        error_type = type("ClientError", (Exception,), {"code": status, "message": "rejected"})
        class FakeModels:
            async def generate_content(self, **kwargs):
                calls["count"] += 1
                raise error_type()
        class FakeAio:
            models = FakeModels()
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
        async def fake_sleep(delay): delays.append(delay)
        monkeypatch.setattr("app.services.reasoning_provider.genai.Client", lambda **kwargs: SimpleNamespace(aio=FakeAio()))
        monkeypatch.setattr("app.services.reasoning_provider.asyncio.sleep", fake_sleep)
        with pytest.raises(HTTPException):
            asyncio.run(GeminiProvider(api_key="test", timeout=10).answer(question="Q", farmer_context="", sources=[], history=[]))
        assert calls["count"] == 1
        assert delays == []


def test_chat_retry_request_id_prevents_duplicate_messages(app_client):
    farmer_id, conversation_id = app_client.test_ids
    body = {"farmer_id": farmer_id, "conversation_id": conversation_id, "message": "Paddy irrigation question", "request_id": "retry-test-001"}
    first = app_client.post("/api/v1/assistant/chat", json=body)
    second = app_client.post("/api/v1/assistant/chat", json=body)
    assert first.status_code == second.status_code == 200
    assert second.json()["answer"] == first.json()["answer"]
    messages = app_client.get(f"/api/v1/conversations/{conversation_id}/messages").json()
    assert [item["role"] for item in messages] == ["user", "assistant"]
