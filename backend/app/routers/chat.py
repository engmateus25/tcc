import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Generator
from app.schemas.dto import ChatRequest, ChatResponse, ChatMessage
from app.services.llm import chat as llm_chat
from app.services.llm import LLMProviderError
from app.services.chat_store import create_session, append_message, get_messages


router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # garante sessão
    session_id = req.session_id or create_session()

    # persiste mensagens do usuário (última é a que o user acabou de enviar)
    try:
        for m in req.messages:
            if m.role in ("user", "system"):
                append_message(session_id, m.role, m.content)
    except Exception as e:
        raise HTTPException(500, f"Erro ao salvar mensagens: {e}")

    # chama LLM
    try:
        content, meta = llm_chat(req.messages, stream=False, provider_name=req.provider)
    except LLMProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_dict()) from exc

    # persiste resposta do assistente
    try:
        append_message(session_id, "assistant", content)
    except Exception as e:
        raise HTTPException(500, f"Erro ao salvar resposta: {e}")

    return ChatResponse(
        content=content,
        model=meta.get("model"),
        provider=meta.get("provider"),
        usage=meta.get("usage"),
        session_id=session_id,
    )

@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    session_id = req.session_id or create_session()

    # salva mensagens do usuário
    try:
        for m in req.messages:
            if m.role in ("user", "system"):
                append_message(session_id, m.role, m.content)
    except Exception as e:
        raise HTTPException(500, f"Erro ao salvar mensagens: {e}")

    try:
        gen, meta = llm_chat(req.messages, stream=True, provider_name=req.provider)  # type: ignore
    except LLMProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.as_dict()) from exc

    def stream_gen() -> Generator[bytes, None, None]:
        # cabeçalho com metadata + session_id
        yield (json.dumps({
            "model": meta.get("model"),
            "provider": meta.get("provider"),
            "session_id": session_id,
            "stream_emulated": meta.get("stream_emulated", False),
        }, ensure_ascii=False) + "\n").encode("utf-8")
        full = []
        for chunk in gen:
            full.append(chunk)
            yield (json.dumps({"delta": chunk}, ensure_ascii=False) + "\n").encode("utf-8")
        # salva a resposta completa ao final
        try:
            append_message(session_id, "assistant", "".join(full))
        except Exception:
            pass

    return StreamingResponse(stream_gen(), media_type="application/x-ndjson")

@router.get("/sessions/{session_id}")
def fetch_session(session_id: str):
    """Retorna o histórico dessa sessão (para reabrir o chat no frontend)."""
    return {"session_id": session_id, "messages": get_messages(session_id)}
