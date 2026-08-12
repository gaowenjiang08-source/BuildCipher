"""Settings service for reading/writing runtime env configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from cipher_genius.api.schemas import EnvSettingsPayload, EnvSettingsResponse
from cipher_genius.utils.config import get_settings


ENV_KEYS = [
    "DEFAULT_LLM_PROVIDER",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "ZHIPUAI_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "QWEN_API_KEY",
    "BAIDU_API_KEY",
    "RELAY_API_KEY",
    "OPENAI_MODEL",
    "ANTHROPIC_MODEL",
    "ZHIPUAI_MODEL",
    "GEMINI_MODEL",
    "DEEPSEEK_MODEL",
    "QWEN_MODEL",
    "BAIDU_MODEL",
    "RELAY_MODEL",
    "OPENAI_BASE_URL",
    "ANTHROPIC_BASE_URL",
    "ZHIPUAI_BASE_URL",
    "GEMINI_BASE_URL",
    "DEEPSEEK_BASE_URL",
    "QWEN_BASE_URL",
    "BAIDU_BASE_URL",
    "RELAY_BASE_URL",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _env_path() -> Path:
    return _project_root() / ".env"


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _looks_masked_secret(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return set(text) == {"*"} or "..." in text


def _parse_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def get_env_settings() -> EnvSettingsResponse:
    path = _env_path()
    file_values = _parse_env_file(path)
    runtime = get_settings()

    values = {
        "default_llm_provider": file_values.get("DEFAULT_LLM_PROVIDER", runtime.default_llm_provider),
        "openai_api_key": _mask(file_values.get("OPENAI_API_KEY", runtime.openai_api_key or "")),
        "anthropic_api_key": _mask(file_values.get("ANTHROPIC_API_KEY", runtime.anthropic_api_key or "")),
        "zhipuai_api_key": _mask(file_values.get("ZHIPUAI_API_KEY", runtime.zhipuai_api_key or "")),
        "gemini_api_key": _mask(file_values.get("GEMINI_API_KEY", runtime.gemini_api_key or "")),
        "deepseek_api_key": _mask(file_values.get("DEEPSEEK_API_KEY", runtime.deepseek_api_key or "")),
        "qwen_api_key": _mask(file_values.get("QWEN_API_KEY", runtime.qwen_api_key or "")),
        "baidu_api_key": _mask(file_values.get("BAIDU_API_KEY", runtime.baidu_api_key or "")),
        "relay_api_key": _mask(file_values.get("RELAY_API_KEY", runtime.relay_api_key or "")),
        "openai_model": file_values.get("OPENAI_MODEL", runtime.openai_model),
        "anthropic_model": file_values.get("ANTHROPIC_MODEL", runtime.anthropic_model),
        "zhipuai_model": file_values.get("ZHIPUAI_MODEL", runtime.zhipuai_model),
        "gemini_model": file_values.get("GEMINI_MODEL", runtime.gemini_model),
        "deepseek_model": file_values.get("DEEPSEEK_MODEL", runtime.deepseek_model),
        "qwen_model": file_values.get("QWEN_MODEL", runtime.qwen_model),
        "baidu_model": file_values.get("BAIDU_MODEL", runtime.baidu_model),
        "relay_model": file_values.get("RELAY_MODEL", runtime.relay_model),
        "openai_base_url": file_values.get("OPENAI_BASE_URL", runtime.openai_base_url or ""),
        "anthropic_base_url": file_values.get("ANTHROPIC_BASE_URL", runtime.anthropic_base_url or ""),
        "zhipuai_base_url": file_values.get("ZHIPUAI_BASE_URL", runtime.zhipuai_base_url or ""),
        "gemini_base_url": file_values.get("GEMINI_BASE_URL", runtime.gemini_base_url or ""),
        "deepseek_base_url": file_values.get("DEEPSEEK_BASE_URL", runtime.deepseek_base_url or ""),
        "qwen_base_url": file_values.get("QWEN_BASE_URL", runtime.qwen_base_url or ""),
        "baidu_base_url": file_values.get("BAIDU_BASE_URL", runtime.baidu_base_url or ""),
        "relay_base_url": file_values.get("RELAY_BASE_URL", runtime.relay_base_url or ""),
    }
    return EnvSettingsResponse(env_path=str(path), values=values, persisted=False)


def update_env_settings(payload: EnvSettingsPayload) -> EnvSettingsResponse:
    path = _env_path()
    if not path.exists():
        path.write_text("", encoding="utf-8")

    updates: Dict[str, Any] = {
        "DEFAULT_LLM_PROVIDER": payload.default_llm_provider,
        "OPENAI_API_KEY": payload.openai_api_key,
        "ANTHROPIC_API_KEY": payload.anthropic_api_key,
        "ZHIPUAI_API_KEY": payload.zhipuai_api_key,
        "GEMINI_API_KEY": payload.gemini_api_key,
        "DEEPSEEK_API_KEY": payload.deepseek_api_key,
        "QWEN_API_KEY": payload.qwen_api_key,
        "BAIDU_API_KEY": payload.baidu_api_key,
        "RELAY_API_KEY": payload.relay_api_key,
        "OPENAI_MODEL": payload.openai_model,
        "ANTHROPIC_MODEL": payload.anthropic_model,
        "ZHIPUAI_MODEL": payload.zhipuai_model,
        "GEMINI_MODEL": payload.gemini_model,
        "DEEPSEEK_MODEL": payload.deepseek_model,
        "QWEN_MODEL": payload.qwen_model,
        "BAIDU_MODEL": payload.baidu_model,
        "RELAY_MODEL": payload.relay_model,
        "OPENAI_BASE_URL": payload.openai_base_url,
        "ANTHROPIC_BASE_URL": payload.anthropic_base_url,
        "ZHIPUAI_BASE_URL": payload.zhipuai_base_url,
        "GEMINI_BASE_URL": payload.gemini_base_url,
        "DEEPSEEK_BASE_URL": payload.deepseek_base_url,
        "QWEN_BASE_URL": payload.qwen_base_url,
        "BAIDU_BASE_URL": payload.baidu_base_url,
        "RELAY_BASE_URL": payload.relay_base_url,
    }

    normalized_updates: Dict[str, str] = {}
    for key, value in updates.items():
        if value is None:
            continue
        if key.endswith("_API_KEY") and _looks_masked_secret(value):
            continue
        normalized_updates[key] = str(value).strip()

    original_lines = path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    touched: set[str] = set()

    for raw_line in original_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(raw_line)
            continue

        key, _ = raw_line.split("=", 1)
        parsed_key = key.strip()
        if parsed_key in normalized_updates:
            new_lines.append(f"{parsed_key}={normalized_updates[parsed_key]}")
            touched.add(parsed_key)
        else:
            new_lines.append(raw_line)

    for key, value in normalized_updates.items():
        if key not in touched:
            new_lines.append(f"{key}={value}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # Refresh pydantic settings cache so new values take effect immediately.
    get_settings.cache_clear()

    snapshot = get_env_settings()
    snapshot.persisted = True
    return snapshot
