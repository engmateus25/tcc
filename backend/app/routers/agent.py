from fastapi import APIRouter, HTTPException
from app.services.agent_langchain import handle_analytics_question
from app.schemas.dto import AgentRequest, AgentResponse
from app.services.chat_store import append_message, create_session, get_messages
from app.services.llm import LLMProviderError

router = APIRouter()

@router.post("/agent", response_model=AgentResponse)
def agent_endpoint(req: AgentRequest):
    """
    Endpoint analitico do AquaMonitor. Ele monta contexto estruturado do
    Firestore e usa o provedor LLM configurado para compor a resposta.
    """
    session_id = req.session_id
    history = []
    storage_error = None

    try:
        session_id = session_id or create_session("AquaMonitor Agent")
        append_message(session_id, "user", req.question)
        history = get_messages(session_id)
    except Exception as exc:
        storage_error = str(exc)

    try:
        result = handle_analytics_question(
            req.question,
            history=history,
            provider_name=req.provider,
        )
    except LLMProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_dict()) from exc

    if session_id and storage_error is None:
        try:
            append_message(session_id, "assistant", result.answer)
        except Exception as exc:
            storage_error = str(exc)

    metadata = dict(result.metadata)
    if storage_error:
        metadata["chat_session_error"] = storage_error

    return AgentResponse(
        answer=result.answer,
        intent=result.intent,
        provider=result.provider,
        model=result.model,
        session_id=session_id,
        usage=result.usage,
        fallback_used=result.fallback_used,
        llm_error=result.llm_error,
        metadata=metadata,
    )
