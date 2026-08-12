"""Unit tests for knowledge base"""

from pathlib import Path

import pytest
from cipher_genius.knowledge.components import ComponentLibrary
from cipher_genius.models.component import ComponentType


def test_component_library_loading():
    """Test component library can load"""
    lib = ComponentLibrary()
    # Should not crash even if directory is empty
    assert lib is not None


def test_component_search():
    """Test component search functionality"""
    lib = ComponentLibrary()

    # Add some test components manually if none exist
    components = lib.list_all()

    # Test search by security level
    secure = lib.find_by_security_level(128)
    assert isinstance(secure, list)

    # If we have components, verify they meet criteria
    if secure:
        for comp in secure:
            assert comp.security.security_level >= 128


def test_get_component():
    """Test getting component by name"""
    lib = ComponentLibrary()

    # Try to get AES if it exists
    aes = lib.get("AES")
    if aes:
        assert aes.name == "AES"
        assert aes.category == ComponentType.BLOCK_CIPHER


def test_find_by_category():
    """Test finding components by category"""
    lib = ComponentLibrary()

    ciphers = lib.find_by_category(ComponentType.BLOCK_CIPHER)
    assert isinstance(ciphers, list)

    if ciphers:
        for cipher in ciphers:
            assert cipher.category == ComponentType.BLOCK_CIPHER


def test_all_component_yaml_files_are_loaded():
    """Ensure no component YAML is silently dropped during library parsing."""
    lib = ComponentLibrary()
    project_root = Path(__file__).resolve().parents[2]
    yaml_count = len(list((project_root / "data" / "components").rglob("*.yaml")))

    assert len(lib.list_all()) == yaml_count
