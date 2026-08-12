"""
安全工具和输入验证
Security utilities and input validation
"""

import re
from typing import Tuple, List
from html import escape


class InputValidator:
    """输入验证器"""

    # 配置
    MAX_INPUT_LENGTH = 2000
    MAX_VARIANTS = 5
    MIN_VARIANTS = 1

    # 危险模式（防止注入攻击）
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # JavaScript
        r'javascript:',  # JavaScript protocol
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>',  # iframes
        r'eval\(',  # eval calls
        r'exec\(',  # exec calls
        r'\$\{.*?\}',  # Template injection
    ]

    @staticmethod
    def validate_requirement_text(text: str) -> Tuple[bool, List[str]]:
        """
        验证需求文本

        Args:
            text: 输入文本

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 检查长度
        if not text or len(text.strip()) == 0:
            errors.append("需求文本不能为空")
            return False, errors

        if len(text) > InputValidator.MAX_INPUT_LENGTH:
            errors.append(f"输入过长（最大{InputValidator.MAX_INPUT_LENGTH}字符）")
            return False, errors

        # 检查危险模式
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append("检测到潜在的安全威胁")
                return False, errors

        # 检查是否有实际内容（不只是空格）
        if len(text.strip()) < 10:
            errors.append("需求描述太短，请提供更多详情")
            return False, errors

        return True, errors

    @staticmethod
    def validate_num_variants(num: int) -> Tuple[bool, List[str]]:
        """
        验证方案变体数量

        Args:
            num: 变体数量

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        if num < InputValidator.MIN_VARIANTS:
            errors.append(f"方案数量至少为{InputValidator.MIN_VARIANTS}")
            return False, errors

        if num > InputValidator.MAX_VARIANTS:
            errors.append(f"方案数量最多为{InputValidator.MAX_VARIANTS}")
            return False, errors

        return True, errors

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        清理文本，移除危险内容

        Args:
            text: 输入文本

        Returns:
            清理后的文本
        """
        # HTML转义
        text = escape(text)

        # 移除危险模式
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """
        检查文件名是否安全

        Args:
            filename: 文件名

        Returns:
            是否安全
        """
        # 只允许字母、数字、下划线、连字符和点
        if not re.match(r'^[\w\-\.]+$', filename):
            return False

        # 不允许路径遍历
        if '..' in filename or '/' in filename or '\\' in filename:
            return False

        # 不允许隐藏文件
        if filename.startswith('.'):
            return False

        return True


class SecurityHeaders:
    """安全HTTP头"""

    @staticmethod
    def get_security_headers() -> dict:
        """
        获取推荐的安全HTTP头

        Returns:
            安全头字典
        """
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
        }


def validate_and_sanitize_input(text: str, max_length: int = 2000) -> Tuple[str, bool, List[str]]:
    """
    验证并清理输入

    Args:
        text: 输入文本
        max_length: 最大长度

    Returns:
        (清理后的文本, 是否有效, 错误列表)
    """
    validator = InputValidator()

    # 先清理
    sanitized = validator.sanitize_text(text)

    # 再验证
    is_valid, errors = validator.validate_requirement_text(sanitized)

    return sanitized, is_valid, errors
