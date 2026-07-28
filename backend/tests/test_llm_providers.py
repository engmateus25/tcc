import pytest

from app.schemas.dto import ChatMessage
from app.services.llm import (
    GeminiProvider,
    LLMProviderError,
    OllamaProvider,
    get_provider,
)


class FakeResponse:
    def __init__(self, data=None, status_code=200, text=""):
        self._data = data or {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._data

    def iter_lines(self, decode_unicode=True):
        yield '{"message":{"content":"ola"},"done":true}'

    def close(self):
        pass


def test_gemini_provider_returns_text_and_metadata(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse(
            {
                "candidates": [
                    {"content": {"parts": [{"text": "Resposta Gemini"}]}}
                ],
                "usageMetadata": {"promptTokenCount": 10},
            }
        )

    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setattr("app.services.llm.requests.post", fake_post)

    content, meta = GeminiProvider().chat(
        [
            ChatMessage(role="system", content="sistema"),
            ChatMessage(role="user", content="pergunta"),
        ]
    )

    assert content == "Resposta Gemini"
    assert meta["provider"] == "gemini"
    assert meta["model"] == "gemini-test"
    assert calls[0]["headers"]["x-goog-api-key"] == "secret"
    assert calls[0]["json"]["systemInstruction"]["parts"][0]["text"] == "sistema"


def test_gemini_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(LLMProviderError) as raised:
        GeminiProvider().chat([ChatMessage(role="user", content="oi")])

    assert raised.value.provider == "gemini"
    assert "GEMINI_API_KEY" in raised.value.message


def test_gemini_provider_maps_quota_errors(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setattr(
        "app.services.llm.requests.post",
        lambda *args, **kwargs: FakeResponse(status_code=429, text="quota"),
    )

    with pytest.raises(LLMProviderError) as raised:
        GeminiProvider().chat([ChatMessage(role="user", content="oi")])

    assert raised.value.status_code == 429
    assert "quota" in raised.value.message.lower()


def test_ollama_provider_returns_text_and_metadata(monkeypatch):
    def fake_post(url, **kwargs):
        return FakeResponse(
            {
                "message": {"content": "Resposta Ollama"},
                "eval_count": 12,
            }
        )

    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b-instruct")
    monkeypatch.setattr("app.services.llm.requests.post", fake_post)

    content, meta = OllamaProvider().chat([ChatMessage(role="user", content="oi")])

    assert content == "Resposta Ollama"
    assert meta["provider"] == "ollama"
    assert meta["model"] == "qwen3:4b-instruct"
    assert meta["usage"]["eval_count"] == 12


def test_invalid_provider_returns_clear_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown")

    with pytest.raises(LLMProviderError) as raised:
        get_provider()

    assert raised.value.status_code == 400
    assert "LLM_PROVIDER invalido" in raised.value.message
