from cipher_genius.utils.config import Settings


def test_buildcipher_governance_path_has_buildtrust_env_compatibility(monkeypatch):
    monkeypatch.delenv("BUILDCIPHER_GOVERNANCE_DATABASE_PATH", raising=False)
    monkeypatch.setenv(
        "BUILDTRUST_GOVERNANCE_DATABASE_PATH",
        ".cache/legacy-buildtrust/governance.sqlite3",
    )

    settings = Settings(_env_file=None)

    assert (
        settings.buildcipher_governance_database_path
        == ".cache/legacy-buildtrust/governance.sqlite3"
    )
    assert (
        settings.buildtrust_governance_database_path
        == settings.buildcipher_governance_database_path
    )
