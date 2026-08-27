from cipher_genius.core.safety_notice import (
    SECURITY_DISCLAIMER_TEXT,
    has_meaningful_artifact,
    with_disclaimer,
)


def test_with_disclaimer_python_prefix():
    content = "print('hello')"
    result = with_disclaimer(content, "python")

    assert SECURITY_DISCLAIMER_TEXT in result
    assert "安全声明" in result
    assert "print('hello')" in result
    assert result.startswith('\"\"\"')


def test_with_disclaimer_c_prefix():
    content = "int main(){return 0;}"
    result = with_disclaimer(content, "c")

    assert SECURITY_DISCLAIMER_TEXT in result
    assert "安全声明" in result
    assert "int main(){return 0;}" in result
    assert result.startswith("/*")


def test_disclaimer_only_is_not_a_code_artifact():
    assert has_meaningful_artifact(with_disclaimer("", "c"), "c") is False
    assert has_meaningful_artifact(with_disclaimer("", "python"), "python") is False
    assert has_meaningful_artifact(with_disclaimer("", "pseudocode"), "pseudocode") is False


def test_implementation_shaped_artifacts_are_recognized():
    assert has_meaningful_artifact("int main(void) { return 0; }", "c") is True
    assert (
        has_meaningful_artifact(
            "def encrypt(message: bytes) -> bytes:\n    return message",
            "python",
        )
        is True
    )
    assert has_meaningful_artifact(
        "function encrypt(key, message):\n"
        "  state = initialize(key)\n"
        "  return process(state, message)",
        "pseudocode",
    ) is True


def test_prose_is_not_misreported_as_implementation():
    assert (
        has_meaningful_artifact(
            "This response explains how C code could be written.",
            "c",
        )
        is False
    )
    assert has_meaningful_artifact("Use authenticated encryption in production.", "python") is False
