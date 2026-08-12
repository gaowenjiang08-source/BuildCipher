"""Enhanced scheme type detection with keyword matching"""

import re
from typing import Tuple, List, Optional
from cipher_genius.models.requirement import SchemeType
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class SchemeTypeDetector:
    """Detect scheme type from requirement description using keywords and patterns"""

    # Keyword patterns for each scheme type (English + Chinese)
    KEYWORDS = {
        SchemeType.AUTHENTICATED_ENCRYPTION: [
            r'\b(authenticated[\s-]?encryption|AEAD|aead|encrypt\s+and\s+authenticate)\b',
            r'\b(GCM|CCM|ChaCha20[\s-]?Poly1305)\b',
            r'\b(integrity\s+and\s+confidentiality)\b',
            # Chinese keywords
            r'(认证加密|加密.*认证|加密.*完整性)',
            r'(保密.*完整性|机密.*认证)',
        ],
        SchemeType.ENCRYPTION: [
            r'\b(encrypt(ion)?|cipher|confidentiality|protect\s+data)\b',
            r'\b(AES|DES|ChaCha20|symmetric)\b',
            r'\b(file\s+encryption|disk\s+encryption|data\s+encryption)\b',
            # Chinese keywords
            r'(加密|密码|保密|对称加密)',
            r'(文件加密|数据加密|磁盘加密)',
        ],
        SchemeType.SIGNATURE: [
            r'\b(sign(ature)?|digital\s+signature|sign\s+message|non[-\s]?repudiation)\b',
            r'\b(RSA\s+sign|ECDSA|Ed25519|DSA)\b',
            r'\b(verify\s+authenticity|prove\s+origin)\b',
            # Chinese keywords
            r'(签名|数字签名|电子签名)',
            r'(验证.*真实性|证明.*来源)',
        ],
        SchemeType.HASH: [
            r'\b(hash|digest|checksum|fingerprint)\b',
            r'\b(SHA[-\s]?\d+|MD5|BLAKE2)\b',
            r'\b(integrity\s+check|verify\s+integrity|detect\s+tamper)\b',
            # Chinese keywords
            r'(哈希|散列|摘要|指纹)',
            r'(完整性.*检查|校验|防篡改)',
        ],
        SchemeType.MAC: [
            r'\b(MAC|message\s+authentication\s+code|HMAC)\b',
            r'\b(authenticate\s+message|verify\s+message)\b',
            # Chinese keywords
            r'(消息认证码|MAC|HMAC)',
            r'(消息认证|报文认证)',
        ],
        SchemeType.KEY_EXCHANGE: [
            r'\b(key[\s-]?exchange|key[\s-]?agreement|shared\s+secret)\b',
            r'\b(Diffie[-\s]?Hellman|DH|ECDH|X25519)\b',
            r'\b(establish\s+key|negotiate\s+key)\b',
            # Chinese keywords
            r'(密钥交换|密钥协商|密钥协议)',
            r'(共享.*密钥|协商.*密钥)',
        ],
        SchemeType.KEY_DERIVATION: [
            r'\b(key[\s-]?derivation|KDF|derive\s+key|password[\s-]?hash)\b',
            r'\b(PBKDF2|bcrypt|scrypt|Argon2|HKDF)\b',
            r'\b(password\s+storage|password\s+hashing)\b',
            # Chinese keywords
            r'(密钥派生|密钥导出|KDF)',
            r'(密码.*哈希|密码.*存储)',
        ],
        SchemeType.RANDOM_NUMBER_GENERATION: [
            r'\b(random|RNG|PRNG|CSPRNG|nonce|IV)\b',
            r'\b(generate\s+random|random\s+number)\b',
            # Chinese keywords
            r'(随机数|随机.*生成|RNG)',
        ],
    }

    # Priority scores - higher score = more specific
    PRIORITY = {
        SchemeType.AUTHENTICATED_ENCRYPTION: 10,  # Most specific
        SchemeType.MAC: 8,
        SchemeType.SIGNATURE: 8,
        SchemeType.KEY_DERIVATION: 7,
        SchemeType.KEY_EXCHANGE: 7,
        SchemeType.HASH: 6,
        SchemeType.RANDOM_NUMBER_GENERATION: 5,
        SchemeType.ENCRYPTION: 3,  # Most general
    }

    # Negative keywords - if these appear, don't use this type
    NEGATIVE_KEYWORDS = {
        SchemeType.ENCRYPTION: [
            r'\b(sign(ature)?|hash|MAC)\b',  # Not just encryption
        ],
        SchemeType.HASH: [
            r'\b(encrypt|sign)\b',  # Not just hash
        ],
    }

    def detect(self, description: str) -> Tuple[Optional[SchemeType], float, List[str]]:
        """
        Detect scheme type from description.

        Args:
            description: Natural language requirement description

        Returns:
            Tuple of (scheme_type, confidence, matched_keywords)
        """
        description_lower = description.lower()

        # Track matches for each type
        matches = {}
        matched_keywords = {}

        for scheme_type, patterns in self.KEYWORDS.items():
            match_count = 0
            keywords = []

            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    match_count += 1
                    keywords.append(pattern.replace(r'\b', '').replace('(', '').replace(')', ''))

            # Check negative keywords
            negative_patterns = self.NEGATIVE_KEYWORDS.get(scheme_type, [])
            has_negative = any(
                re.search(pattern, description, re.IGNORECASE)
                for pattern in negative_patterns
            )

            if match_count > 0 and not has_negative:
                # Calculate score based on matches and priority
                score = match_count * self.PRIORITY[scheme_type]
                matches[scheme_type] = score
                matched_keywords[scheme_type] = keywords

        # No matches
        if not matches:
            logger.warning("No scheme type keywords matched in description")
            return None, 0.0, []

        # Get best match
        best_type = max(matches.items(), key=lambda x: x[1])[0]
        best_score = matches[best_type]

        # Calculate confidence (0-1)
        # More matches and higher priority = higher confidence
        max_possible_score = len(self.KEYWORDS[best_type]) * self.PRIORITY[best_type]
        confidence = min(1.0, best_score / max_possible_score * 1.5)  # Scale up a bit

        # Adjust confidence based on how clear the winner is
        if len(matches) > 1:
            # Sort by score
            sorted_matches = sorted(matches.values(), reverse=True)
            if len(sorted_matches) >= 2:
                # If second best is close, reduce confidence
                ratio = sorted_matches[0] / sorted_matches[1] if sorted_matches[1] > 0 else 2.0
                if ratio < 1.5:
                    confidence *= 0.8  # Reduce confidence if ambiguous

        logger.info(f"Detected scheme type: {best_type.value} (confidence: {confidence:.2f})")
        logger.debug(f"Matched keywords: {matched_keywords[best_type]}")

        return best_type, confidence, matched_keywords[best_type]

    def detect_with_fallback(
        self,
        description: str,
        llm_detected: Optional[SchemeType] = None,
        llm_confidence: float = 0.0
    ) -> Tuple[SchemeType, float, str]:
        """
        Detect scheme type with fallback to LLM result.

        Args:
            description: Natural language requirement description
            llm_detected: Scheme type detected by LLM (optional)
            llm_confidence: LLM detection confidence (optional)

        Returns:
            Tuple of (scheme_type, confidence, source)
            - source: "keyword", "llm", or "combined"
        """
        keyword_type, keyword_conf, keywords = self.detect(description)

        # Only keywords detected
        if keyword_type and not llm_detected:
            return keyword_type, keyword_conf, "keyword"

        # Only LLM detected
        if llm_detected and not keyword_type:
            return llm_detected, llm_confidence, "llm"

        # Both detected - compare
        if keyword_type and llm_detected:
            # If they agree, high confidence
            if keyword_type == llm_detected:
                combined_conf = min(1.0, (keyword_conf + llm_confidence) / 2 * 1.2)
                logger.info(f"Keyword and LLM agree: {keyword_type.value} (combined confidence: {combined_conf:.2f})")
                return keyword_type, combined_conf, "combined"

            # They disagree - use the one with higher confidence
            if keyword_conf > llm_confidence:
                logger.warning(
                    f"Keyword detection ({keyword_type.value}, {keyword_conf:.2f}) "
                    f"overrides LLM ({llm_detected.value}, {llm_confidence:.2f})"
                )
                return keyword_type, keyword_conf, "keyword"
            else:
                logger.warning(
                    f"LLM detection ({llm_detected.value}, {llm_confidence:.2f}) "
                    f"overrides keyword ({keyword_type.value}, {keyword_conf:.2f})"
                )
                return llm_detected, llm_confidence, "llm"

        # Neither detected - this shouldn't happen if called correctly
        logger.error("No scheme type detected by keyword or LLM")
        return SchemeType.ENCRYPTION, 0.5, "default"


def detect_scheme_type(description: str) -> Tuple[Optional[SchemeType], float]:
    """
    Convenience function to detect scheme type.

    Args:
        description: Natural language requirement description

    Returns:
        Tuple of (scheme_type, confidence)
    """
    detector = SchemeTypeDetector()
    scheme_type, confidence, _ = detector.detect(description)
    return scheme_type, confidence
