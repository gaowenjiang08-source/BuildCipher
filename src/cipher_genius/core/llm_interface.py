"""LLM interface for interacting with language models."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from urllib.parse import quote

from cipher_genius.utils.cache import get_cache
from cipher_genius.utils.config import get_settings
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class LLMInterface(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """Generate text from prompt."""

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate JSON response from prompt."""

    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        schema_name: str = "structured_output",
    ) -> Dict[str, Any]:
        """Generate schema-constrained output.

        Default implementation falls back to `generate_json`; providers can override
        for native schema-constrained generation.
        """
        return self.generate_json(prompt, system_prompt=system_prompt, temperature=temperature)


class OpenAIInterface(LLMInterface):
    """OpenAI API interface."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.base_url = base_url if base_url is not None else settings.openai_base_url

        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        try:
            from openai import OpenAI

            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)
        except ImportError as exc:
            raise ImportError("openai package not installed. Install with: poetry add openai") from exc

    def _cached_get(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        cache = get_cache()
        return cache.get(
            prompt=prompt,
            system_prompt=system_prompt or "",
            temperature=temperature,
            model=self.model,
            schema=json.dumps(schema, sort_keys=True) if schema else "",
        )

    def _cached_set(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response: Dict[str, Any],
        temperature: float,
        schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        cache = get_cache()
        cache.set(
            prompt=prompt,
            system_prompt=system_prompt or "",
            response=response,
            temperature=temperature,
            model=self.model,
            schema=json.dumps(schema, sort_keys=True) if schema else "",
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """Generate text from prompt."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate JSON response from prompt."""
        cached_result = self._cached_get(prompt, system_prompt, temperature)
        if cached_result is not None:
            logger.debug("Cache HIT for OpenAI JSON request")
            return cached_result

        logger.debug("Cache MISS for OpenAI JSON request, calling API")

        full_prompt = prompt + "\n\nRespond with valid JSON only."
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": full_prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI JSON response parsing failed: {exc}") from exc

        self._cached_set(prompt, system_prompt, result, temperature)
        return result

    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        schema_name: str = "structured_output",
    ) -> Dict[str, Any]:
        """Generate schema-constrained output using OpenAI structured outputs."""
        cached_result = self._cached_get(prompt, system_prompt, temperature, schema=schema)
        if cached_result is not None:
            logger.debug("Cache HIT for OpenAI structured request")
            return cached_result

        logger.debug("Cache MISS for OpenAI structured request, calling API")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        )

        content = response.choices[0].message.content or "{}"
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI structured response parsing failed: {exc}") from exc

        self._cached_set(prompt, system_prompt, result, temperature, schema=schema)
        return result


class AnthropicInterface(LLMInterface):
    """Anthropic API interface."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        self.base_url = base_url if base_url is not None else settings.anthropic_base_url

        if not self.api_key:
            raise ValueError("Anthropic API key not provided")

        try:
            from anthropic import Anthropic

            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = Anthropic(**kwargs)
        except ImportError as exc:
            raise ImportError("anthropic package not installed. Install with: poetry add anthropic") from exc

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """Generate text from prompt."""
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        if not response.content:
            return ""
        return getattr(response.content[0], "text", "")

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate JSON response from prompt."""
        cache = get_cache()
        cached_result = cache.get(
            prompt=prompt,
            system_prompt=system_prompt or "",
            temperature=temperature,
            model=self.model,
        )
        if cached_result is not None:
            logger.debug("Cache HIT for Anthropic request")
            return cached_result

        full_prompt = prompt + "\n\nRespond with valid JSON only."
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4000,
            "temperature": temperature,
            "messages": [{"role": "user", "content": full_prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        if not response.content:
            raise ValueError("Anthropic returned empty response")

        content = getattr(response.content[0], "text", "")
        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Anthropic JSON response parsing failed: {exc}") from exc

        cache.set(
            prompt=prompt,
            system_prompt=system_prompt or "",
            response=result,
            temperature=temperature,
            model=self.model,
        )
        return result


class ZhipuAIInterface(LLMInterface):
    """ZhipuAI (GLM) API interface."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.zhipuai_api_key
        self.model = model or settings.zhipuai_model
        self.base_url = base_url if base_url is not None else settings.zhipuai_base_url

        if not self.api_key:
            raise ValueError("ZhipuAI API key not provided")

        try:
            from zhipuai import ZhipuAI

            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            try:
                self.client = ZhipuAI(**kwargs)
            except TypeError:
                # Older SDKs may not support custom base_url.
                self.client = ZhipuAI(api_key=self.api_key)
        except ImportError as exc:
            raise ImportError("zhipuai package not installed. Install with: pip install zhipuai") from exc

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """Generate text from prompt."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate JSON response from prompt."""
        cache = get_cache()
        cached_result = cache.get(
            prompt=prompt,
            system_prompt=system_prompt or "",
            temperature=temperature,
            model=self.model,
        )
        if cached_result is not None:
            logger.debug("Cache HIT for ZhipuAI request")
            return cached_result

        full_prompt = prompt + "\n\nOnly return valid JSON."
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": full_prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ZhipuAI JSON response parsing failed: {exc}") from exc

        cache.set(
            prompt=prompt,
            system_prompt=system_prompt or "",
            response=result,
            temperature=temperature,
            model=self.model,
        )
        return result


class OpenAICompatibleInterface(OpenAIInterface):
    """OpenAI-compatible gateway for relay and domestic model providers."""

    def __init__(
        self,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        settings = get_settings()
        defaults: Dict[str, Dict[str, Optional[str]]] = {
            "deepseek": {
                "api_key": settings.deepseek_api_key,
                "model": settings.deepseek_model,
                "base_url": settings.deepseek_base_url,
            },
            "qwen": {
                "api_key": settings.qwen_api_key,
                "model": settings.qwen_model,
                "base_url": settings.qwen_base_url,
            },
            "baidu": {
                "api_key": settings.baidu_api_key,
                "model": settings.baidu_model,
                "base_url": settings.baidu_base_url,
            },
            "relay": {
                "api_key": settings.relay_api_key,
                "model": settings.relay_model,
                "base_url": settings.relay_base_url,
            },
        }
        config = defaults.get(provider, defaults["relay"])
        resolved_base_url = base_url if base_url is not None else config.get("base_url")
        if not resolved_base_url:
            raise ValueError(f"{provider} base_url not provided")
        super().__init__(
            api_key=api_key or config.get("api_key"),
            model=model or config.get("model"),
            base_url=resolved_base_url,
        )


class GeminiInterface(LLMInterface):
    """Google Gemini API interface using the REST endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.base_url = (base_url if base_url is not None else settings.gemini_base_url) or (
            "https://generativelanguage.googleapis.com/v1beta"
        )
        if not self.api_key:
            raise ValueError("Gemini API key not provided")

    def _endpoint(self) -> str:
        root = str(self.base_url or "").rstrip("/")
        return f"{root}/models/{quote(str(self.model), safe='')}:generateContent?key={self.api_key}"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("httpx package not installed. Install with: poetry add httpx") from exc

        text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        response = httpx.post(self._endpoint(), json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates") or []
        parts = ((candidates[0] or {}).get("content") or {}).get("parts") if candidates else []
        return "\n".join(str(part.get("text") or "") for part in (parts or [])).strip()

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        content = self.generate(
            prompt=f"{prompt}\n\nOnly return valid JSON.",
            system_prompt=system_prompt,
            temperature=temperature,
        )
        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            return json.loads(content or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Gemini JSON response parsing failed: {exc}") from exc


def get_llm_interface(
    provider: Optional[str] = None,
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMInterface:
    """Get LLM interface based on provider."""
    settings = get_settings()
    resolved_provider = (provider or settings.default_llm_provider or "openai").lower()

    if resolved_provider == "openai":
        return OpenAIInterface(api_key=api_key, model=model, base_url=base_url)
    if resolved_provider in {"anthropic", "claude"}:
        return AnthropicInterface(api_key=api_key, model=model, base_url=base_url)
    if resolved_provider in {"gemini", "google"}:
        return GeminiInterface(api_key=api_key, model=model, base_url=base_url)
    if resolved_provider in {"zhipuai", "glm"}:
        return ZhipuAIInterface(api_key=api_key, model=model, base_url=base_url)
    if resolved_provider in {"deepseek"}:
        return OpenAICompatibleInterface("deepseek", api_key=api_key, model=model, base_url=base_url)
    if resolved_provider in {"qwen", "tongyi", "dashscope"}:
        return OpenAICompatibleInterface("qwen", api_key=api_key, model=model, base_url=base_url)
    if resolved_provider in {"baidu", "wenxin", "qianfan"}:
        return OpenAICompatibleInterface("baidu", api_key=api_key, model=model, base_url=base_url)
    if resolved_provider in {"relay", "openai_compatible", "custom"}:
        return OpenAICompatibleInterface("relay", api_key=api_key, model=model, base_url=base_url)
    raise ValueError(f"Unknown LLM provider: {resolved_provider}")
