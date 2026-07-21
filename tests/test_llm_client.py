import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import llm_client
from llm_client import LLMClient, LLMError, get_llm_client, reset_llm_client


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_llm_client()
    yield
    reset_llm_client()


def test_client_disabled_when_ai_not_configured(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", False)
    monkeypatch.setattr(config, "AI_DISABLED_REASON", "AI features are disabled for this test.")
    client = LLMClient()
    assert client.is_available() is False
    assert "disabled" in client.unavailable_reason().lower()


def test_generate_text_raises_when_unavailable(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", False)
    monkeypatch.setattr(config, "AI_DISABLED_REASON", "not configured")
    client = LLMClient()
    with pytest.raises(LLMError):
        client.generate_text("hello")


def test_get_llm_client_is_a_singleton(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", False)
    c1 = get_llm_client()
    c2 = get_llm_client()
    assert c1 is c2


def test_reset_llm_client_forces_new_instance(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", False)
    c1 = get_llm_client()
    reset_llm_client()
    c2 = get_llm_client()
    assert c1 is not c2


def test_generate_json_parses_plain_json(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", False)
    client = LLMClient()
    client.generate_text = lambda prompt: '{"a": 1, "b": "two"}'
    result = client.generate_json("irrelevant prompt")
    assert result == {"a": 1, "b": "two"}


def test_generate_json_strips_code_fences(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", False)
    client = LLMClient()
    client.generate_text = lambda prompt: '```json\n{"x": 42}\n```'
    result = client.generate_json("irrelevant prompt")
    assert result == {"x": 42}


def test_generate_json_raises_on_invalid_json(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", False)
    client = LLMClient()
    client.generate_text = lambda prompt: "not json at all"
    with pytest.raises(LLMError):
        client.generate_json("irrelevant prompt")


def test_client_initializes_with_current_genai_sdk_when_configured(monkeypatch):
    """
    Exercises the real google.genai.Client(api_key=...) construction path
    (migration target). No network call is made — Client() only builds a
    request object, it doesn't validate the key until a call is issued.
    """
    monkeypatch.setattr(config, "AI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-test-key-not-real")
    monkeypatch.setattr(config, "GEMINI_MODEL", "gemini-2.0-flash")
    client = LLMClient()
    assert client.is_available() is True
    assert client._init_error is None
    assert client._genai_client is not None


class _FakeAPIError(Exception):
    def __init__(self, code, status, message="error"):
        self.code = code
        self.status = status
        self.message = message
        super().__init__(f"{code} {status}: {message}")


def test_quota_exhausted_gets_friendly_message(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", True)
    client = LLMClient()
    client.enabled = True

    class _FakeModels:
        def generate_content(self, model, contents):
            raise _FakeAPIError(429, "RESOURCE_EXHAUSTED")

    class _FakeGenaiClient:
        models = _FakeModels()

    client._genai_client = _FakeGenaiClient()
    client._model = "gemini-test"

    with pytest.raises(LLMError) as exc_info:
        client.generate_text("hello")
    assert "quota" in str(exc_info.value).lower()


def test_transient_unavailable_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", True)
    monkeypatch.setattr(llm_client, "_RETRY_DELAY_SECONDS", 0)  # don't actually sleep in tests
    client = LLMClient()
    client.enabled = True

    call_count = {"n": 0}

    class _FakeResponse:
        text = "eventual success"

    class _FakeModels:
        def generate_content(self, model, contents):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise _FakeAPIError(503, "UNAVAILABLE")
            return _FakeResponse()

    class _FakeGenaiClient:
        models = _FakeModels()

    client._genai_client = _FakeGenaiClient()
    client._model = "gemini-test"

    result = client.generate_text("hello")
    assert result == "eventual success"
    assert call_count["n"] == 2


def test_transient_unavailable_exhausts_retries_and_raises_friendly_error(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", True)
    monkeypatch.setattr(llm_client, "_RETRY_DELAY_SECONDS", 0)
    client = LLMClient()
    client.enabled = True

    class _FakeModels:
        def generate_content(self, model, contents):
            raise _FakeAPIError(503, "UNAVAILABLE")

    class _FakeGenaiClient:
        models = _FakeModels()

    client._genai_client = _FakeGenaiClient()
    client._model = "gemini-test"

    with pytest.raises(LLMError) as exc_info:
        client.generate_text("hello")
    assert "overloaded" in str(exc_info.value).lower()


def test_non_retryable_error_fails_immediately_without_retry(monkeypatch):
    monkeypatch.setattr(config, "AI_ENABLED", True)
    client = LLMClient()
    client.enabled = True

    call_count = {"n": 0}

    class _FakeModels:
        def generate_content(self, model, contents):
            call_count["n"] += 1
            raise _FakeAPIError(403, "PERMISSION_DENIED")

    class _FakeGenaiClient:
        models = _FakeModels()

    client._genai_client = _FakeGenaiClient()
    client._model = "gemini-test"

    with pytest.raises(LLMError) as exc_info:
        client.generate_text("hello")
    assert call_count["n"] == 1  # no retry for a non-transient error
    assert "api_key" in str(exc_info.value).lower() or "gemini_api_key" in str(exc_info.value).lower()
