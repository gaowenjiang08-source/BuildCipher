"""Safety disclaimer helpers for generated cryptographic artifacts."""

from __future__ import annotations

SECURITY_DISCLAIMER_TEXT = (
    "安全声明：本输出由 AI 生成，仅用于研究、方案讨论与教育用途。"
    "其并不直接等同于可生产部署的密码系统，任何上线前都必须经过独立的专业密码评审、"
    "形式化验证与安全审计。"
)


def get_disclaimer(language: str) -> str:
    """Return language-specific disclaimer block."""
    lang = (language or "").lower()

    if lang == "python":
        return (
            '"""\n'
            f"{SECURITY_DISCLAIMER_TEXT}\n"
            '"""\n\n'
        )

    if lang == "c":
        return (
            "/*\n"
            f" * {SECURITY_DISCLAIMER_TEXT}\n"
            " */\n\n"
        )

    if lang == "pseudocode":
        return (
            f"# {SECURITY_DISCLAIMER_TEXT}\n\n"
        )

    return f"{SECURITY_DISCLAIMER_TEXT}\n\n"


def with_disclaimer(content: str, language: str) -> str:
    """Prefix content with a mandatory safety disclaimer."""
    body = (content or "").lstrip()
    return f"{get_disclaimer(language)}{body}"
