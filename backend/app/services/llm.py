import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import requests

from app.schemas.dto import ChatMessage


DEFAULT_TIMEOUT_SECONDS = 120.0


class LLMProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: Optional[str] = None,
        status_code: int = 503,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.details = details or {}

    def as_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "provider": self.provider,
            "model": self.model,
            "details": self.details,
        }


@dataclass(frozen=True)
class LLMMetadata:
    provider: str
    model: str
    usage: Optional[Any] = None
    stream_emulated: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "usage": self.usage,
            "stream_emulated": self.stream_emulated,
        }


class LLMProvider:
    provider_name: str
    model: str

    def chat(
        self,
        messages: List[ChatMessage],
        *,
        stream: bool = False,
    ) -> Tuple[str | Generator[str, None, None], Dict[str, Any]]:
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    provider_name = "ollama"

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")
        self.timeout = _env_float("OLLAMA_TIMEOUT_SECONDS", 600.0)
        self.temperature = _env_float("LLM_TEMPERATURE", 0.3)
        self.max_tokens = _env_int("LLM_MAX_TOKENS", 1024)

    def chat(
        self,
        messages: List[ChatMessage],
        *,
        stream: bool = False,
    ) -> Tuple[str | Generator[str, None, None], Dict[str, Any]]:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "stream": stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        if not stream:
            response = self._post(url, payload, stream=False)
            data = _decode_json_response(response, self.provider_name, self.model)
            content = data.get("message", {}).get("content", "") or ""
            usage = {
                key: data.get(key)
                for key in (
                    "total_duration",
                    "load_duration",
                    "prompt_eval_count",
                    "eval_count",
                    "eval_duration",
                )
                if key in data
            } or None
            return content, LLMMetadata("ollama", self.model, usage=usage).as_dict()

        def gen() -> Generator[str, None, None]:
            response = self._post(url, payload, stream=True)
            try:
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    chunk = obj.get("message", {}).get("content", "") or ""
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        break
            finally:
                response.close()

        return gen(), LLMMetadata("ollama", self.model).as_dict()

    def _post(self, url: str, payload: Dict[str, Any], *, stream: bool):
        try:
            response = requests.post(
                url,
                json=payload,
                stream=stream,
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            raise LLMProviderError(
                f"Ollama indisponivel em {self.base_url}. Inicie o Ollama e baixe o modelo {self.model}.",
                provider="ollama",
                model=self.model,
                status_code=503,
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise LLMProviderError(
                f"Timeout ao consultar Ollama apos {self.timeout:.0f}s.",
                provider="ollama",
                model=self.model,
                status_code=504,
            ) from exc
        except requests.RequestException as exc:
            raise LLMProviderError(
                f"Falha ao consultar Ollama: {exc}",
                provider="ollama",
                model=self.model,
                status_code=503,
            ) from exc

        if response.status_code >= 400:
            detail = _safe_response_text(response)
            message = (
                f"Modelo Ollama nao encontrado: {self.model}. Rode `ollama pull {self.model}`."
                if response.status_code == 404
                else f"Ollama retornou HTTP {response.status_code}."
            )
            response.close()
            raise LLMProviderError(
                message,
                provider="ollama",
                model=self.model,
                status_code=503,
                details={"response": detail},
            )

        return response


class OpenAIProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = _env_float("LLM_TEMPERATURE", 0.3)
        self.max_tokens = _env_int("LLM_MAX_TOKENS", 1024)
        self.api_key = os.getenv("OPENAI_API_KEY")

    def chat(
        self,
        messages: List[ChatMessage],
        *,
        stream: bool = False,
    ) -> Tuple[str | Generator[str, None, None], Dict[str, Any]]:
        if not self.api_key:
            raise LLMProviderError(
                "OPENAI_API_KEY nao configurada no backend.",
                provider="openai",
                model=self.model,
                status_code=503,
            )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            if not stream:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[m.model_dump() for m in messages],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                content = resp.choices[0].message.content or ""
                usage = getattr(resp, "usage", None)
                return content, LLMMetadata(
                    "openai",
                    self.model,
                    usage=usage.model_dump() if usage else None,
                ).as_dict()

            def gen() -> Generator[str, None, None]:
                with client.chat.completions.create(
                    model=self.model,
                    messages=[m.model_dump() for m in messages],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True,
                ) as stream_resp:
                    for event in stream_resp:
                        delta = event.choices[0].delta.content or ""
                        if delta:
                            yield delta

            return gen(), LLMMetadata("openai", self.model).as_dict()
        except Exception as exc:
            status_code = int(getattr(exc, "status_code", 503) or 503)
            if status_code == 401:
                message = "OPENAI_API_KEY invalida ou sem permissao."
            elif status_code == 429:
                message = "Limite ou quota da OpenAI atingido."
            else:
                message = f"Falha ao consultar OpenAI: {exc}"
            raise LLMProviderError(
                message,
                provider="openai",
                model=self.model,
                status_code=_normalize_http_status(status_code),
            ) from exc


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self):
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.base_url = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta",
        ).rstrip("/")
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.temperature = _env_float("LLM_TEMPERATURE", 0.3)
        self.max_tokens = _env_int("LLM_MAX_TOKENS", 1024)
        self.timeout = _env_float("GEMINI_TIMEOUT_SECONDS", 60.0)

    def chat(
        self,
        messages: List[ChatMessage],
        *,
        stream: bool = False,
    ) -> Tuple[str | Generator[str, None, None], Dict[str, Any]]:
        if not self.api_key:
            raise LLMProviderError(
                "GEMINI_API_KEY nao configurada no backend.",
                provider="gemini",
                model=self.model,
                status_code=503,
            )

        if stream:
            content, meta = self.chat(messages, stream=False)

            def gen() -> Generator[str, None, None]:
                yield str(content)

            meta["stream_emulated"] = True
            return gen(), meta

        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = self._build_payload(messages)

        try:
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise LLMProviderError(
                f"Timeout ao consultar Gemini apos {self.timeout:.0f}s.",
                provider="gemini",
                model=self.model,
                status_code=504,
            ) from exc
        except requests.RequestException as exc:
            raise LLMProviderError(
                f"Falha ao consultar Gemini: {exc}",
                provider="gemini",
                model=self.model,
                status_code=503,
            ) from exc

        if response.status_code >= 400:
            detail = _safe_response_text(response)
            status_code = _normalize_http_status(response.status_code)
            if response.status_code in (401, 403):
                message = "GEMINI_API_KEY invalida, ausente ou sem permissao para o modelo."
            elif response.status_code == 429:
                message = "Limite ou quota da Gemini API atingido."
            elif response.status_code >= 500:
                message = "Gemini API indisponivel no momento."
            else:
                message = f"Gemini API retornou HTTP {response.status_code}."
            raise LLMProviderError(
                message,
                provider="gemini",
                model=self.model,
                status_code=status_code,
                details={"response": detail},
            )

        data = _decode_json_response(response, "gemini", self.model)
        content = _extract_gemini_text(data)
        if not content:
            raise LLMProviderError(
                "Gemini nao retornou texto na resposta.",
                provider="gemini",
                model=self.model,
                status_code=502,
                details={"response": data},
            )

        return content, LLMMetadata(
            "gemini",
            self.model,
            usage=data.get("usageMetadata"),
        ).as_dict()

    def _build_payload(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        system_parts = [m.content for m in messages if m.role == "system"]
        contents: List[Dict[str, Any]] = []

        for message in messages:
            if message.role == "system":
                continue
            role = "model" if message.role == "assistant" else "user"
            part = {"text": message.content}
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"].append(part)
            else:
                contents.append({"role": role, "parts": [part]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": ""}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

        if system_parts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_parts)}],
            }

        return payload


def available_provider_names() -> List[str]:
    return ["ollama", "gemini", "openai"]


def get_provider(provider_name: Optional[str] = None) -> LLMProvider:
    provider = (provider_name or os.getenv("LLM_PROVIDER", "ollama")).strip().lower()
    if provider == "gemini":
        return GeminiProvider()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "ollama":
        return OllamaProvider()

    raise LLMProviderError(
        f"LLM_PROVIDER invalido: {provider}. Use um de: {', '.join(available_provider_names())}.",
        provider=provider or "unknown",
        status_code=400,
    )


def chat(
    messages: List[ChatMessage],
    stream: bool = False,
    provider_name: Optional[str] = None,
):
    provider = get_provider(provider_name)
    return provider.chat(messages, stream=stream)


def _decode_json_response(response, provider: str, model: str) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError as exc:
        raise LLMProviderError(
            f"{provider} retornou uma resposta nao JSON.",
            provider=provider,
            model=model,
            status_code=502,
            details={"response": _safe_response_text(response)},
        ) from exc


def _extract_gemini_text(data: Dict[str, Any]) -> str:
    chunks: List[str] = []
    for candidate in data.get("candidates", []) or []:
        content = candidate.get("content") or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if text:
                chunks.append(text)
    return "".join(chunks).strip()


def _safe_response_text(response) -> str:
    try:
        return response.text[:1000]
    except Exception:
        return ""


def _normalize_http_status(status_code: int) -> int:
    if status_code in (400, 401, 403, 404, 408, 409, 422, 429, 502, 503, 504):
        return status_code
    if status_code >= 500:
        return 503
    return 503


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
