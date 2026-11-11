"""Fixtures compartilhadas para manter testes isolados dos dados locais."""

import pytest


@pytest.fixture(autouse=True)
def usar_banco_temporario(tmp_path, monkeypatch):
    """Evita que operações de teste leiam ou alterem data/jurisprudencia.db."""
    import database

    monkeypatch.setattr(
        database.connection,
        "DB_PATH",
        tmp_path / "jurisprudencia-teste.db",
    )
    database.init_db()
