"""PlayzAI Multi-AI Provider Architecture.

Provides abstractions and implementations for:
- Google Gemini
- OpenAI
- Anthropic Claude
- OpenAI-compatible endpoints (Groq, Together, DeepSeek, Ollama, OpenRouter, vLLM, etc.)
- Custom HTTP AI endpoints

Each provider uses its authentic API protocol, request payload format, and response parser.
All errors map to standard safe AI exception types.
"""

from __future__ import annotations

import json
import time
from typing import Any
import httpx


class AIError(Exception):
    """Base exception for AI provider operations."""

    code: str = "ai_error"
    status_code: int = 500

    def __init__(self, message: str = "", code: str | None = None, status_code: int | None = None):
        super().__init__(message or self.__class__.__name__)
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class ProviderNotConfigured(AIError):
    code = "provider_not_configured"
    status_code = 503


class InvalidAPIKey(AIError):
    code = "invalid_api_key"
    status_code = 401


class AuthenticationFailed(AIError):
    code = "authentication_failed"
    status_code = 401


class RateLimited(AIError):
    code = "rate_limited"
    status_code = 429


class InsufficientQuota(AIError):
    code = "insufficient_quota"
    status_code = 429


class ProviderUnavailable(AIError):
    code = "provider_unavailable"
    status_code = 503


class ProviderTimedOut(AIError):
    code = "provider_timeout"
    status_code = 504


class InvalidModel(AIError):
    code = "invalid_model"
    status_code = 400


class InvalidRequest(AIError):
    code = "invalid_request"
    status_code = 400


class UnsupportedProvider(AIError):
    code = "unsupported_provider"
    status_code = 400


class NetworkError(AIError):
    code = "network_error"
    status_code = 503


class InvalidProviderResponse(AIError):
    code = "invalid_provider_response"
    status_code = 502


# Legacy aliases for backward compatibility with existing tests
ProviderRejected = AuthenticationFailed


def mask_api_key(key: str | None) -> str:
    """Mask an API key for safe display in UI and non-secret outputs."""
    if not key:
        return ""
    key = key.strip()
    if len(key) <= 8:
        return "•" * len(key)
    return f"{key[:4]}••••••••{key[-4:]}"


def build_system_prompt(base_prompt: str, language: str = "en") -> str:
    """Enhance system prompt with appropriate language instructions."""
    lang_lower = (language or "en").lower().strip()
    if lang_lower in ("hi", "hindi"):
        lang_instruction = (
            "You are PlayzAI, a helpful, precise AI assistant. "
            "The user has selected Hindi. Respond truthfully and naturally in Hindi using Devanagari script. "
            "Never fake system information or command results."
        )
    elif lang_lower in ("hinglish", "hi-en", "en-in"):
        lang_instruction = (
            "You are PlayzAI, a helpful, precise AI assistant. "
            "The user has selected Hinglish. Respond naturally in Indian Hinglish using Roman script "
            "(for example: 'Haan bilkul, main aapke PC ka status check karta hoon.'). "
            "Keep the tone friendly, helpful, and natural. Never fake system information or command results."
        )
    else:
        lang_instruction = (
            "You are PlayzAI, a truthful, secure AI assistant and PC automation controller. "
            "Respond clearly, concisely, and truthfully in English. "
            "Never fabricate command output or PC telemetry."
        )

    if base_prompt:
        return f"{base_prompt}\n\nLanguage & Style Directive:\n{lang_instruction}"
    return lang_instruction


class AIProvider:
    """Abstract base class for all AI providers."""

    provider_type: str = "base"
    default_base_url: str = ""
    default_model: str = ""
    default_models: list[str] = []

    async def test_connection(
        self,
        api_key: str,
        base_url: str = "",
        model: str = "",
        timeout_seconds: float = 12.0,
    ) -> dict[str, Any]:
        """Test authentication and connectivity with the provider."""
        raise NotImplementedError

    async def discover_models(
        self,
        api_key: str,
        base_url: str = "",
        timeout_seconds: float = 12.0,
    ) -> list[str]:
        """Discover available models from the provider."""
        return list(self.default_models)

    async def generate_response(
        self,
        message: str,
        conversation_history: list[dict[str, str]],
        api_key: str,
        base_url: str = "",
        model: str = "",
        system_prompt: str = "",
        language: str = "en",
        max_tokens: int = 1000,
        timeout_seconds: float = 25.0,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Generate a chat response from the provider."""
        raise NotImplementedError


class GeminiProvider(AIProvider):
    """Google Gemini AI Provider using the official Google Generative Language REST API."""

    provider_type = "gemini"
    default_base_url = "https://generativelanguage.googleapis.com"
    default_model = "gemini-1.5-flash"
    default_models = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash-exp",
        "gemini-1.0-pro",
    ]

    def _clean_base_url(self, base_url: str) -> str:
        return (base_url or self.default_base_url).strip().rstrip("/")

    async def test_connection(
        self,
        api_key: str,
        base_url: str = "",
        model: str = "",
        timeout_seconds: float = 12.0,
    ) -> dict[str, Any]:
        if not api_key or not api_key.strip():
            return {
                "ok": False,
                "error_code": "invalid_api_key",
                "detail": "API key cannot be empty.",
                "latency_ms": 0,
            }

        url = f"{self._clean_base_url(base_url)}/v1beta/models?key={api_key.strip()}"
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

            if response.status_code == 200:
                data = response.json()
                models = [
                    m.get("name", "").replace("models/", "")
                    for m in data.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "models": models or self.default_models,
                    "detail": f"Successfully connected to Google Gemini. Found {len(models)} models.",
                }
            elif response.status_code == 400:
                body = response.text
                if "API_KEY_INVALID" in body or "API key not valid" in body:
                    return {
                        "ok": False,
                        "error_code": "invalid_api_key",
                        "detail": "Invalid Google Gemini API key.",
                        "latency_ms": latency_ms,
                    }
                return {
                    "ok": False,
                    "error_code": "invalid_request",
                    "detail": f"Gemini returned HTTP 400: {response.json().get('error', {}).get('message', 'Bad request')}",
                    "latency_ms": latency_ms,
                }
            elif response.status_code in (401, 403):
                return {
                    "ok": False,
                    "error_code": "authentication_failed",
                    "detail": "Gemini authentication failed (HTTP 401/403). Check API key permissions.",
                    "latency_ms": latency_ms,
                }
            elif response.status_code == 429:
                return {
                    "ok": False,
                    "error_code": "rate_limited",
                    "detail": "Gemini rate limit or quota exceeded (HTTP 429).",
                    "latency_ms": latency_ms,
                }
            elif response.status_code >= 500:
                return {
                    "ok": False,
                    "error_code": "provider_unavailable",
                    "detail": f"Gemini server error (HTTP {response.status_code}).",
                    "latency_ms": latency_ms,
                }
            else:
                return {
                    "ok": False,
                    "error_code": "invalid_provider_response",
                    "detail": f"Gemini returned unexpected status HTTP {response.status_code}.",
                    "latency_ms": latency_ms,
                }
        except httpx.TimeoutException:
            return {
                "ok": False,
                "error_code": "provider_timeout",
                "detail": "Connection to Google Gemini timed out.",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "error_code": "network_error",
                "detail": f"Network error connecting to Gemini: {exc.__class__.__name__}",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }

    async def discover_models(
        self,
        api_key: str,
        base_url: str = "",
        timeout_seconds: float = 12.0,
    ) -> list[str]:
        if not api_key:
            return list(self.default_models)
        url = f"{self._clean_base_url(base_url)}/v1beta/models?key={api_key.strip()}"
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
            if response.status_code == 200:
                data = response.json()
                models = [
                    m.get("name", "").replace("models/", "")
                    for m in data.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                if models:
                    return models
        except Exception:
            pass
        return list(self.default_models)

    async def generate_response(
        self,
        message: str,
        conversation_history: list[dict[str, str]],
        api_key: str,
        base_url: str = "",
        model: str = "",
        system_prompt: str = "",
        language: str = "en",
        max_tokens: int = 1000,
        timeout_seconds: float = 25.0,
        request_id: str = "",
    ) -> dict[str, Any]:
        if not api_key or not api_key.strip():
            raise ProviderNotConfigured("Gemini API key is not configured.")

        target_model = (model or self.default_model).strip()
        url = f"{self._clean_base_url(base_url)}/v1beta/models/{target_model}:generateContent?key={api_key.strip()}"

        # Construct contents for Gemini API
        contents = []
        for turn in conversation_history:
            role = "user" if turn.get("role") == "user" else "model"
            text = turn.get("content") or turn.get("body") or ""
            if text:
                contents.append({"role": role, "parts": [{"text": text}]})

        contents.append({"role": "user", "parts": [{"text": message}]})

        sys_prompt_text = build_system_prompt(system_prompt, language)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7,
            },
            "systemInstruction": {
                "parts": [{"text": sys_prompt_text}]
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimedOut("Gemini request timed out.") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error connecting to Gemini: {exc}") from exc

        if response.status_code == 400:
            body = response.text
            if "API_KEY_INVALID" in body or "API key not valid" in body:
                raise InvalidAPIKey("Invalid Google Gemini API key.")
            raise InvalidRequest(f"Gemini invalid request: {response.text[:200]}")
        elif response.status_code in (401, 403):
            raise AuthenticationFailed("Gemini authentication failed.")
        elif response.status_code == 404:
            raise InvalidModel(f"Gemini model '{target_model}' not found.")
        elif response.status_code == 429:
            raise RateLimited("Gemini quota or rate limit exceeded.")
        elif response.status_code >= 500:
            raise ProviderUnavailable(f"Gemini service unavailable (HTTP {response.status_code}).")
        elif response.status_code < 200 or response.status_code >= 300:
            raise InvalidProviderResponse(f"Gemini returned HTTP {response.status_code}.")

        try:
            res_data = response.json()
            candidates = res_data.get("candidates", [])
            if not candidates:
                raise InvalidProviderResponse("Gemini returned empty candidate list.")
            parts = candidates[0].get("content", {}).get("parts", [])
            reply_text = "".join(p.get("text", "") for p in parts).strip()
            if not reply_text:
                raise InvalidProviderResponse("Gemini returned blank response.")
            return {
                "reply": reply_text,
                "model": target_model,
                "provider": "gemini",
                "raw": res_data,
            }
        except (KeyError, IndexError, ValueError) as exc:
            raise InvalidProviderResponse(f"Failed to parse Gemini response: {exc}") from exc


class OpenAIProvider(AIProvider):
    """OpenAI API Provider using the standard OpenAI Chat Completions API."""

    provider_type = "openai"
    default_base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o-mini"
    default_models = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "o1-mini",
        "o1-preview",
    ]

    def _clean_base_url(self, base_url: str) -> str:
        return (base_url or self.default_base_url).strip().rstrip("/")

    async def test_connection(
        self,
        api_key: str,
        base_url: str = "",
        model: str = "",
        timeout_seconds: float = 12.0,
    ) -> dict[str, Any]:
        if not api_key or not api_key.strip():
            return {
                "ok": False,
                "error_code": "invalid_api_key",
                "detail": "API key cannot be empty.",
                "latency_ms": 0,
            }

        url = f"{self._clean_base_url(base_url)}/models"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Accept": "application/json",
        }
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers=headers)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

            if response.status_code == 200:
                data = response.json()
                models = [
                    m.get("id", "")
                    for m in data.get("data", [])
                    if any(prefix in m.get("id", "") for prefix in ("gpt-", "o1-", "chatgpt-"))
                ]
                models.sort()
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "models": models or self.default_models,
                    "detail": f"Successfully connected to OpenAI. Found {len(models)} chat models.",
                }
            elif response.status_code == 401:
                return {
                    "ok": False,
                    "error_code": "invalid_api_key",
                    "detail": "Invalid OpenAI API key (HTTP 401 Unauthorized).",
                    "latency_ms": latency_ms,
                }
            elif response.status_code == 429:
                return {
                    "ok": False,
                    "error_code": "rate_limited",
                    "detail": "OpenAI rate limit or quota exceeded (HTTP 429). Check your billing/credits.",
                    "latency_ms": latency_ms,
                }
            elif response.status_code >= 500:
                return {
                    "ok": False,
                    "error_code": "provider_unavailable",
                    "detail": f"OpenAI server error (HTTP {response.status_code}).",
                    "latency_ms": latency_ms,
                }
            else:
                return {
                    "ok": False,
                    "error_code": "invalid_provider_response",
                    "detail": f"OpenAI returned HTTP {response.status_code}: {response.text[:200]}",
                    "latency_ms": latency_ms,
                }
        except httpx.TimeoutException:
            return {
                "ok": False,
                "error_code": "provider_timeout",
                "detail": "Connection to OpenAI timed out.",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "error_code": "network_error",
                "detail": f"Network error connecting to OpenAI: {exc.__class__.__name__}",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }

    async def discover_models(
        self,
        api_key: str,
        base_url: str = "",
        timeout_seconds: float = 12.0,
    ) -> list[str]:
        if not api_key:
            return list(self.default_models)
        url = f"{self._clean_base_url(base_url)}/models"
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                models = [
                    m.get("id", "")
                    for m in data.get("data", [])
                    if any(prefix in m.get("id", "") for prefix in ("gpt-", "o1-", "chatgpt-"))
                ]
                if models:
                    models.sort()
                    return models
        except Exception:
            pass
        return list(self.default_models)

    async def generate_response(
        self,
        message: str,
        conversation_history: list[dict[str, str]],
        api_key: str,
        base_url: str = "",
        model: str = "",
        system_prompt: str = "",
        language: str = "en",
        max_tokens: int = 1000,
        timeout_seconds: float = 25.0,
        request_id: str = "",
    ) -> dict[str, Any]:
        if not api_key or not api_key.strip():
            raise ProviderNotConfigured("OpenAI API key is not configured.")

        target_model = (model or self.default_model).strip()
        endpoint = f"{self._clean_base_url(base_url)}/chat/completions"

        sys_prompt_text = build_system_prompt(system_prompt, language)
        messages = [{"role": "system", "content": sys_prompt_text}]

        for turn in conversation_history:
            role = turn.get("role", "user")
            text = turn.get("content") or turn.get("body") or ""
            if text:
                messages.append({"role": role, "content": text})

        messages.append({"role": "user", "content": message})

        payload = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimedOut("OpenAI request timed out.") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error connecting to OpenAI: {exc}") from exc

        if response.status_code == 401:
            raise InvalidAPIKey("Invalid OpenAI API key.")
        elif response.status_code == 404:
            raise InvalidModel(f"OpenAI model '{target_model}' not found.")
        elif response.status_code == 429:
            raise RateLimited("OpenAI quota or rate limit exceeded.")
        elif response.status_code >= 500:
            raise ProviderUnavailable(f"OpenAI service unavailable (HTTP {response.status_code}).")
        elif response.status_code < 200 or response.status_code >= 300:
            raise InvalidProviderResponse(f"OpenAI returned HTTP {response.status_code}.")

        try:
            res_data = response.json()
            reply = res_data["choices"][0]["message"]["content"]
            if not isinstance(reply, str) or not reply.strip():
                raise InvalidProviderResponse("OpenAI returned blank message content.")
            return {
                "reply": reply.strip(),
                "model": target_model,
                "provider": "openai",
                "raw": res_data,
            }
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise InvalidProviderResponse(f"Failed to parse OpenAI response: {exc}") from exc


class ClaudeProvider(AIProvider):
    """Anthropic Claude API Provider using the Anthropic Messages API."""

    provider_type = "claude"
    default_base_url = "https://api.anthropic.com/v1"
    default_model = "claude-3-5-sonnet-20241022"
    default_models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def _clean_base_url(self, base_url: str) -> str:
        return (base_url or self.default_base_url).strip().rstrip("/")

    async def test_connection(
        self,
        api_key: str,
        base_url: str = "",
        model: str = "",
        timeout_seconds: float = 12.0,
    ) -> dict[str, Any]:
        if not api_key or not api_key.strip():
            return {
                "ok": False,
                "error_code": "invalid_api_key",
                "detail": "API key cannot be empty.",
                "latency_ms": 0,
            }

        endpoint = f"{self._clean_base_url(base_url)}/messages"
        target_model = (model or self.default_model).strip()
        headers = {
            "x-api-key": api_key.strip(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": target_model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

            if response.status_code == 200:
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "models": self.default_models,
                    "detail": "Successfully connected to Anthropic Claude.",
                }
            elif response.status_code in (401, 403):
                return {
                    "ok": False,
                    "error_code": "invalid_api_key",
                    "detail": "Invalid Anthropic API key (HTTP 401/403).",
                    "latency_ms": latency_ms,
                }
            elif response.status_code == 429:
                return {
                    "ok": False,
                    "error_code": "rate_limited",
                    "detail": "Anthropic rate limit exceeded (HTTP 429).",
                    "latency_ms": latency_ms,
                }
            elif response.status_code == 404:
                return {
                    "ok": False,
                    "error_code": "invalid_model",
                    "detail": f"Claude model '{target_model}' not found (HTTP 404).",
                    "latency_ms": latency_ms,
                }
            elif response.status_code >= 500:
                return {
                    "ok": False,
                    "error_code": "provider_unavailable",
                    "detail": f"Anthropic service error (HTTP {response.status_code}).",
                    "latency_ms": latency_ms,
                }
            else:
                return {
                    "ok": False,
                    "error_code": "invalid_request",
                    "detail": f"Anthropic returned HTTP {response.status_code}: {response.text[:200]}",
                    "latency_ms": latency_ms,
                }
        except httpx.TimeoutException:
            return {
                "ok": False,
                "error_code": "provider_timeout",
                "detail": "Connection to Anthropic Claude timed out.",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "error_code": "network_error",
                "detail": f"Network error connecting to Anthropic: {exc.__class__.__name__}",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }

    async def discover_models(
        self,
        api_key: str,
        base_url: str = "",
        timeout_seconds: float = 12.0,
    ) -> list[str]:
        return list(self.default_models)

    async def generate_response(
        self,
        message: str,
        conversation_history: list[dict[str, str]],
        api_key: str,
        base_url: str = "",
        model: str = "",
        system_prompt: str = "",
        language: str = "en",
        max_tokens: int = 1000,
        timeout_seconds: float = 25.0,
        request_id: str = "",
    ) -> dict[str, Any]:
        if not api_key or not api_key.strip():
            raise ProviderNotConfigured("Anthropic Claude API key is not configured.")

        target_model = (model or self.default_model).strip()
        endpoint = f"{self._clean_base_url(base_url)}/messages"

        sys_prompt_text = build_system_prompt(system_prompt, language)

        messages = []
        for turn in conversation_history:
            role = turn.get("role", "user")
            text = turn.get("content") or turn.get("body") or ""
            if text:
                messages.append({"role": role, "content": text})

        messages.append({"role": "user", "content": message})

        payload = {
            "model": target_model,
            "system": sys_prompt_text,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        headers = {
            "x-api-key": api_key.strip(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimedOut("Anthropic Claude request timed out.") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error connecting to Claude: {exc}") from exc

        if response.status_code in (401, 403):
            raise AuthenticationFailed("Invalid Anthropic Claude API key.")
        elif response.status_code == 404:
            raise InvalidModel(f"Claude model '{target_model}' not found.")
        elif response.status_code == 429:
            raise RateLimited("Anthropic Claude rate limit exceeded.")
        elif response.status_code >= 500:
            raise ProviderUnavailable(f"Anthropic Claude service unavailable (HTTP {response.status_code}).")
        elif response.status_code < 200 or response.status_code >= 300:
            raise InvalidProviderResponse(f"Claude returned HTTP {response.status_code}: {response.text[:200]}")

        try:
            res_data = response.json()
            content_blocks = res_data.get("content", [])
            reply = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            if not reply.strip():
                raise InvalidProviderResponse("Claude returned empty text content.")
            return {
                "reply": reply.strip(),
                "model": target_model,
                "provider": "claude",
                "raw": res_data,
            }
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise InvalidProviderResponse(f"Failed to parse Claude response: {exc}") from exc


class OpenAICompatibleProvider(AIProvider):
    """Universal OpenAI-compatible Provider (Groq, Together, DeepSeek, Ollama, OpenRouter, vLLM, etc.)."""

    provider_type = "openai_compatible"
    default_base_url = "https://api.groq.com/openai/v1"
    default_model = "llama-3.3-70b-versatile"
    default_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "deepseek-chat",
        "deepseek-reasoner",
        "mistral-large-latest",
    ]

    def _clean_base_url(self, base_url: str) -> str:
        url = (base_url or self.default_base_url).strip().rstrip("/")
        return url

    async def test_connection(
        self,
        api_key: str,
        base_url: str = "",
        model: str = "",
        timeout_seconds: float = 12.0,
    ) -> dict[str, Any]:
        clean_url = self._clean_base_url(base_url)
        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        start_time = time.perf_counter()
        # First attempt /models discovery endpoint
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(f"{clean_url}/models", headers=headers)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", "") for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "models": models or self.default_models,
                    "detail": f"Successfully connected to OpenAI-compatible endpoint. Found {len(models)} models.",
                }
            elif response.status_code == 401:
                return {
                    "ok": False,
                    "error_code": "invalid_api_key",
                    "detail": "Authentication failed (HTTP 401). Check API key.",
                    "latency_ms": latency_ms,
                }
            elif response.status_code == 429:
                return {
                    "ok": False,
                    "error_code": "rate_limited",
                    "detail": "Rate limit or quota exceeded (HTTP 429).",
                    "latency_ms": latency_ms,
                }
        except httpx.TimeoutException:
            return {
                "ok": False,
                "error_code": "provider_timeout",
                "detail": "Connection to endpoint timed out.",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "error_code": "network_error",
                "detail": f"Network error connecting to endpoint: {exc.__class__.__name__}",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }

        # If /models is not implemented, try a minimal completion test
        target_model = (model or self.default_model).strip()
        endpoint = clean_url if clean_url.endswith("/chat/completions") else f"{clean_url}/chat/completions"
        try:
            payload = {
                "model": target_model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            }
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                res = await client.post(endpoint, json=payload, headers=headers)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
            if res.status_code == 200:
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "models": [target_model],
                    "detail": f"Successfully connected to {clean_url}.",
                }
            elif res.status_code == 401:
                return {
                    "ok": False,
                    "error_code": "invalid_api_key",
                    "detail": "Authentication failed (HTTP 401). Check API key.",
                    "latency_ms": latency_ms,
                }
            elif res.status_code == 429:
                return {
                    "ok": False,
                    "error_code": "rate_limited",
                    "detail": "Rate limit exceeded (HTTP 429).",
                    "latency_ms": latency_ms,
                }
            else:
                return {
                    "ok": False,
                    "error_code": "invalid_provider_response",
                    "detail": f"Endpoint returned HTTP {res.status_code}.",
                    "latency_ms": latency_ms,
                }
        except Exception as exc:
            return {
                "ok": False,
                "error_code": "network_error",
                "detail": f"Error contacting endpoint: {exc}",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }

    async def discover_models(
        self,
        api_key: str,
        base_url: str = "",
        timeout_seconds: float = 12.0,
    ) -> list[str]:
        clean_url = self._clean_base_url(base_url)
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(f"{clean_url}/models", headers=headers)
            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", "") for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]
                if models:
                    models.sort()
                    return models
        except Exception:
            pass
        return list(self.default_models)

    async def generate_response(
        self,
        message: str,
        conversation_history: list[dict[str, str]],
        api_key: str,
        base_url: str = "",
        model: str = "",
        system_prompt: str = "",
        language: str = "en",
        max_tokens: int = 1000,
        timeout_seconds: float = 25.0,
        request_id: str = "",
    ) -> dict[str, Any]:
        clean_url = self._clean_base_url(base_url)
        if not clean_url:
            raise ProviderNotConfigured("OpenAI-compatible base URL is not configured.")

        target_model = (model or self.default_model).strip()
        endpoint = clean_url if clean_url.endswith("/chat/completions") else f"{clean_url}/chat/completions"

        sys_prompt_text = build_system_prompt(system_prompt, language)
        messages = [{"role": "system", "content": sys_prompt_text}]

        for turn in conversation_history:
            role = turn.get("role", "user")
            text = turn.get("content") or turn.get("body") or ""
            if text:
                messages.append({"role": role, "content": text})

        messages.append({"role": "user", "content": message})

        payload = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimedOut("Endpoint request timed out.") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error connecting to endpoint: {exc}") from exc

        if response.status_code == 401:
            raise InvalidAPIKey("Authentication failed for custom endpoint.")
        elif response.status_code == 404:
            raise InvalidModel(f"Model '{target_model}' not found on endpoint.")
        elif response.status_code == 429:
            raise RateLimited("Rate limit exceeded on endpoint.")
        elif response.status_code >= 500:
            raise ProviderUnavailable(f"Endpoint service unavailable (HTTP {response.status_code}).")
        elif response.status_code < 200 or response.status_code >= 300:
            raise InvalidProviderResponse(f"Endpoint returned HTTP {response.status_code}.")

        try:
            res_data = response.json()
            reply = res_data["choices"][0]["message"]["content"]
            if not isinstance(reply, str) or not reply.strip():
                raise InvalidProviderResponse("Endpoint returned blank content.")
            return {
                "reply": reply.strip(),
                "model": target_model,
                "provider": "openai_compatible",
                "raw": res_data,
            }
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise InvalidProviderResponse(f"Failed to parse endpoint response: {exc}") from exc


class CustomProvider(AIProvider):
    """Custom HTTP AI Endpoint Provider."""

    provider_type = "custom"
    default_base_url = "http://127.0.0.1:11434/api/generate"
    default_model = "custom-model"
    default_models = ["custom-model"]

    async def test_connection(
        self,
        api_key: str,
        base_url: str = "",
        model: str = "",
        timeout_seconds: float = 12.0,
    ) -> dict[str, Any]:
        url = (base_url or self.default_base_url).strip()
        if not url:
            return {"ok": False, "error_code": "invalid_request", "detail": "Base URL cannot be empty."}

        headers: dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        start_time = time.perf_counter()
        try:
            # Check if reachable via GET or HEAD
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                try:
                    response = await client.get(url, headers=headers)
                except httpx.HTTPStatusError:
                    response = await client.post(url, json={"prompt": "ping", "model": model or self.default_model}, headers=headers)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
            if response.status_code in (200, 204, 404, 405):
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "models": [model or self.default_model],
                    "detail": f"Successfully reached custom endpoint (HTTP {response.status_code}).",
                }
            elif response.status_code == 401:
                return {"ok": False, "error_code": "invalid_api_key", "detail": "Unauthorized (HTTP 401).", "latency_ms": latency_ms}
            else:
                return {"ok": False, "error_code": "invalid_provider_response", "detail": f"HTTP {response.status_code}", "latency_ms": latency_ms}
        except httpx.TimeoutException:
            return {"ok": False, "error_code": "provider_timeout", "detail": "Connection timed out.", "latency_ms": round((time.perf_counter() - start_time) * 1000, 1)}
        except Exception as exc:
            return {"ok": False, "error_code": "network_error", "detail": str(exc), "latency_ms": round((time.perf_counter() - start_time) * 1000, 1)}

    async def generate_response(
        self,
        message: str,
        conversation_history: list[dict[str, str]],
        api_key: str,
        base_url: str = "",
        model: str = "",
        system_prompt: str = "",
        language: str = "en",
        max_tokens: int = 1000,
        timeout_seconds: float = 25.0,
        request_id: str = "",
    ) -> dict[str, Any]:
        url = (base_url or self.default_base_url).strip()
        if not url:
            raise ProviderNotConfigured("Custom endpoint URL is not configured.")

        target_model = (model or self.default_model).strip()
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        if request_id:
            headers["X-Request-ID"] = request_id

        sys_prompt_text = build_system_prompt(system_prompt, language)
        payload = {
            "model": target_model,
            "prompt": f"{sys_prompt_text}\n\nUser: {message}",
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimedOut("Custom endpoint request timed out.") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error connecting to custom endpoint: {exc}") from exc

        if response.status_code == 401:
            raise InvalidAPIKey("Authentication failed on custom endpoint.")
        elif response.status_code >= 500:
            raise ProviderUnavailable(f"Custom endpoint returned HTTP {response.status_code}.")
        elif response.status_code != 200:
            raise InvalidProviderResponse(f"Custom endpoint returned HTTP {response.status_code}.")

        try:
            res_data = response.json()
            reply = res_data.get("response") or res_data.get("reply") or res_data.get("text")
            if not reply and "choices" in res_data:
                reply = res_data["choices"][0]["message"]["content"]
            if not isinstance(reply, str) or not reply.strip():
                raise InvalidProviderResponse("Custom endpoint returned empty response.")
            return {
                "reply": reply.strip(),
                "model": target_model,
                "provider": "custom",
                "raw": res_data,
            }
        except Exception as exc:
            raise InvalidProviderResponse(f"Failed to parse custom response: {exc}") from exc


PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "custom": CustomProvider,
}


def get_provider_instance(provider_type: str) -> AIProvider:
    """Instantiate a provider adapter by type string."""
    ptype = (provider_type or "").lower().strip()
    cls = PROVIDER_REGISTRY.get(ptype)
    if not cls:
        raise UnsupportedProvider(f"Unsupported provider type '{provider_type}'. Supported: {list(PROVIDER_REGISTRY.keys())}")
    return cls()
