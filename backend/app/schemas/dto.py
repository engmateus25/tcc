from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Literal, Optional, Any
from datetime import datetime, timezone


# ===== Chat =====
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Histórico no formato OpenAI")
    stream: bool = False
    session_id: Optional[str] = None
    provider: Optional[str] = None

class ChatResponse(BaseModel):
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    usage: Optional[Any] = None
    session_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

# ===== Reports =====
class ReportRequest(BaseModel):
    period: Literal["7d", "30d", "90d"] = "7d"

class ReportSummary(BaseModel):
    total_events: int
    by_sensor: dict
    by_action: dict

class ReportResponse(BaseModel):
    period: str
    summary: ReportSummary
    pdf_url: Optional[str] = None   # caso for salvar em Storage no futuro


# ===== Agent =====
class AquaIntent(BaseModel):
    """
    Representa a intenção interpretada da pergunta do usuário no contexto AquaMonitor.
    """

    kind: Literal[
        "summary_all",             # resumo de todos os sensores
        "summary_low",             # resumo focado no sensor de nível baixo
        "count_events_all",        # contar todos os eventos (alto/baixo, subiu/desceu)
        "count_low",               # quantas vezes caixa ficou vazia (sensor baixo DESCEU)
        "count_full",              # quantas vezes caixa ficou cheia (sensor alto SUBIU)
        "duration_empty",          # tempo total caixa vazia
        "duration_full",           # tempo total caixa cheia
        "count_empty_and_full",    # contar vazio e cheio na mesma resposta
        "count_and_duration_empty",# quantas vezes + quanto tempo vazia
        "count_and_duration_full", # quantas vezes + quanto tempo cheia
        "health_check",            # sensores apresentaram inconsistência?
        "water_consumption",       # estimativa de consumo de agua/custo
        "energy_consumption",      # energia/custo da bomba
        "alerts_summary",          # resumo dos alertas abertos
        "smalltalk",               # quem é você / o que você faz / etc.
        "unknown",
    ] = "unknown"

    period: Optional[str] = None        # "2d", "20d", "this_week", "this_month", etc
    sensor: Optional[Literal["baixo", "alto"]] = None
    estado: Optional[Literal["subiu", "desceu"]] = None

class AgentRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    provider: Optional[str] = None

class AgentResponse(BaseModel):
    answer: str
    intent: AquaIntent
    provider: Optional[str] = None
    model: Optional[str] = None
    session_id: Optional[str] = None
    usage: Optional[Any] = None
    fallback_used: bool = False
    llm_error: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


# ==== Alerts / Cloud Function ====
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SensorEventIn(BaseModel):
    sensor: Literal["baixo", "alto"]
    estado: Literal["subiu", "desceu"]
    timestamp: datetime = Field(default_factory=utc_now)
    device_id: Optional[str] = None
    document_id: Optional[str] = None
    event_id: Optional[str] = None
    source: Optional[str] = "unknown"
    raw_path: Optional[str] = None
    received_at: Optional[datetime] = None
    timestamp_missing: bool = False

    @model_validator(mode="before")
    @classmethod
    def mark_missing_timestamp(cls, data: Any) -> Any:
        if isinstance(data, dict):
            normalized = dict(data)
            normalized["timestamp_missing"] = not bool(normalized.get("timestamp"))
            return normalized
        return data

    @field_validator("sensor", "estado", mode="before")
    @classmethod
    def normalize_required_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("device_id", "document_id", "event_id", "source", "raw_path", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return str(value)

    @field_validator("timestamp", mode="before")
    @classmethod
    def default_missing_timestamp(cls, value: Any) -> Any:
        return value or utc_now()

    @field_validator("timestamp", "received_at")
    @classmethod
    def normalize_datetime(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class SensorEventProcessResponse(BaseModel):
    processed: bool
    duplicate: bool
    event_id: str
    processing_key: Optional[str] = None
    processing_status: Optional[str] = None
    payload_hash_mismatch: Optional[bool] = None
    alerts_created: List[dict] = Field(default_factory=list)
    cycle_created: Optional[Any] = None
    autocloud: dict = Field(default_factory=dict)


class AlertListResponse(BaseModel):
    total: int
    alerts: List[dict] = Field(default_factory=list)


class AlertAcknowledgeResponse(BaseModel):
    id: str
    acknowledged: bool
    status: str
    acknowledged_at: datetime
