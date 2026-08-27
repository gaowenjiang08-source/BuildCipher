"""Safety disclaimer helpers for generated cryptographic artifacts."""

from __future__ import annotations

import ast
import re

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


def has_meaningful_artifact(content: str, language: str) -> bool:
    """Return whether generated text contains an implementation-shaped artifact.

    A disclaimer or prose-only response is not a code artifact. This predicate is
    intentionally narrower than compilation: compilation and sandbox execution
    remain separate verification stages.
    """
    body = (content or "").strip()
    if not body:
        return False

    lang = (language or "").lower()
    if lang in {"c", "cpp", "c++"}:
        without_comments = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
        without_comments = re.sub(r"//.*", "", without_comments)
        return bool(
            re.search(
                r"\b[A-Za-z_]\w*(?:\s+|\s*\*\s*)+[A-Za-z_]\w*\s*\([^;{}]*\)\s*\{",
                without_comments,
            )
        )

    if lang == "python":
        try:
            module = ast.parse(body)
        except SyntaxError:
            return False
        statements = module.body
        if statements and isinstance(statements[0], ast.Expr):
            value = statements[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                statements = statements[1:]
        return any(
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            for node in statements
        )

    if lang == "pseudocode":
        lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "//"))
        ]
        algorithm_marker = re.compile(
            r"\b(function|procedure|algorithm|encrypt|decrypt|sign|verify)\b",
            flags=re.IGNORECASE,
        )
        return len(lines) >= 3 and any(algorithm_marker.search(line) for line in lines)

    return False
