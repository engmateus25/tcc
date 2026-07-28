from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.routers import agent as agent_router
from app.routers import chat as chat_router
from app.schemas.dto import AgentRequest, AquaIntent, ChatMessage, ChatRequest
from app.services import agent_langchain
from app.services.agent_langchain import AgentResult, handle_analytics_question
from app.services.llm import LLMProviderError


BASE = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def sensor_event(seconds, sensor, estado):
    return {
        "sensor": sensor,
        "estado": estado,
        "timestamp": BASE + timedelta(seconds=seconds),
    }


def patch_agent_context(monkeypatch):
    monkeypatch.setattr(
        agent_langchain,
        "fetch_sensor_events",
        lambda period: [
            sensor_event(0, "baixo", "desceu"),
            sensor_event(600, "baixo", "subiu"),
            sensor_event(1200, "baixo", "desceu"),
            sensor_event(1800, "alto", "subiu"),
        ],
    )
    monkeypatch.setattr(
        agent_langchain,
        "get_consumption_summary",
        lambda period: {
            "total_liters": 500.0,
            "cycle_count": 1,
            "average_liters_per_day": 71.4,
            "total_cost_brl": 4.0,
        },
    )
    monkeypatch.setattr(
        agent_langchain,
        "get_energy_summary",
        lambda period: {
            "total_kwh": 0.75,
            "total_on_minutes": 60,
            "total_cost_brl": 0.49,
        },
    )
    monkeypatch.setattr(agent_langchain, "list_alerts", lambda **kwargs: [])


def test_agent_deterministic_mode_counts_empty_events(monkeypatch):
    patch_agent_context(monkeypatch)
    monkeypatch.setenv("AGENT_RESPONSE_MODE", "deterministic")

    result = handle_analytics_question(
        "Quantas vezes a caixa ficou vazia nos últimos 7 dias?"
    )

    assert result.intent.kind == "count_low"
    assert result.fallback_used is True
    assert "2 vez" in result.answer


def test_agent_hybrid_uses_llm_with_structured_context(monkeypatch):
    patch_agent_context(monkeypatch)
    monkeypatch.setenv("AGENT_RESPONSE_MODE", "hybrid")
    captured = {}

    def fake_llm(messages, stream=False, provider_name=None):
        captured["messages"] = messages
        captured["provider_name"] = provider_name
        return "Resposta melhorada pelo modelo.", {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "usage": {"promptTokenCount": 100},
        }

    monkeypatch.setattr(agent_langchain, "llm_chat", fake_llm)

    result = handle_analytics_question(
        "Me dê um resumo dos eventos dos sensores nesta semana.",
        provider_name="gemini",
    )

    assert result.answer == "Resposta melhorada pelo modelo."
    assert result.provider == "gemini"
    assert result.model == "gemini-2.5-flash"
    assert result.fallback_used is False
    assert captured["provider_name"] == "gemini"
    assert "Contexto estruturado" in captured["messages"][1].content


def test_agent_fallback_is_explicit_when_llm_fails(monkeypatch):
    patch_agent_context(monkeypatch)
    monkeypatch.setenv("AGENT_RESPONSE_MODE", "hybrid")
    monkeypatch.setenv("AGENT_ALLOW_DETERMINISTIC_FALLBACK", "1")

    def fake_llm(*args, **kwargs):
        raise LLMProviderError(
            "Ollama indisponivel",
            provider="ollama",
            model="qwen3:4b-instruct",
        )

    monkeypatch.setattr(agent_langchain, "llm_chat", fake_llm)

    result = handle_analytics_question("Quanto a bomba consumiu nos últimos 7 dias?")

    assert result.fallback_used is True
    assert result.provider == "ollama"
    assert result.llm_error == "Ollama indisponivel"
    assert "0.750 kWh" in result.answer


def test_agent_endpoint_returns_session_and_model_metadata(monkeypatch):
    monkeypatch.setattr(agent_router, "create_session", lambda title: "session-1")
    monkeypatch.setattr(agent_router, "append_message", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        agent_router,
        "get_messages",
        lambda session_id: [{"role": "user", "content": "oi"}],
    )
    monkeypatch.setattr(
        agent_router,
        "handle_analytics_question",
        lambda question, history, provider_name: AgentResult(
            answer="ok",
            intent=AquaIntent(kind="smalltalk"),
            provider="gemini",
            model="gemini-2.5-flash",
        ),
    )

    response = agent_router.agent_endpoint(AgentRequest(question="oi"))

    assert response.answer == "ok"
    assert response.session_id == "session-1"
    assert response.provider == "gemini"
    assert response.model == "gemini-2.5-flash"


def test_agent_endpoint_maps_llm_provider_error(monkeypatch):
    monkeypatch.setattr(agent_router, "create_session", lambda title: "session-1")
    monkeypatch.setattr(agent_router, "append_message", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_router, "get_messages", lambda session_id: [])

    def fail(*args, **kwargs):
        raise LLMProviderError(
            "GEMINI_API_KEY nao configurada",
            provider="gemini",
            model="gemini-2.5-flash",
            status_code=503,
        )

    monkeypatch.setattr(agent_router, "handle_analytics_question", fail)

    with pytest.raises(HTTPException) as raised:
        agent_router.agent_endpoint(AgentRequest(question="oi", provider="gemini"))

    assert raised.value.status_code == 503
    assert raised.value.detail["provider"] == "gemini"


def test_chat_endpoint_returns_provider_model_and_session(monkeypatch):
    monkeypatch.setattr(chat_router, "create_session", lambda title="AquaMonitor Chat": "chat-1")
    monkeypatch.setattr(chat_router, "append_message", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        chat_router,
        "llm_chat",
        lambda messages, stream=False, provider_name=None: (
            "resposta",
            {"provider": "ollama", "model": "qwen3:4b-instruct", "usage": None},
        ),
    )

    response = chat_router.chat(
        ChatRequest(
            messages=[ChatMessage(role="user", content="oi")],
            provider="ollama",
        )
    )

    assert response.content == "resposta"
    assert response.session_id == "chat-1"
    assert response.provider == "ollama"
    assert response.model == "qwen3:4b-instruct"
