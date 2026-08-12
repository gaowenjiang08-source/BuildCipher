from cipher_genius.core.safety_notice import SECURITY_DISCLAIMER_TEXT, with_disclaimer


def test_with_disclaimer_python_prefix():
    content = "print('hello')"
    result = with_disclaimer(content, "python")

    assert SECURITY_DISCLAIMER_TEXT in result
    assert "安全声明" in result
    assert "print('hello')" in result
    assert result.startswith('"""')


def test_with_disclaimer_c_prefix():
    content = "int main(){return 0;}"
    result = with_disclaimer(content, "c")

    assert SECURITY_DISCLAIMER_TEXT in result
    assert "安全声明" in result
    assert "int main(){return 0;}" in result
    assert result.startswith("/*")
