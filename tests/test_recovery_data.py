from database import listar_decisoes
from database import connection
import recovery_data


def test_recovered_public_data_has_official_sources_and_no_fiction():
    assert recovery_data.REGISTROS_PUBLICOS_RECUPERADOS
    assert all(row["link_oficial"].startswith("https://") for row in recovery_data.REGISTROS_PUBLICOS_RECUPERADOS)
    assert all("EXEMPLO" not in row["titulo"].upper() for row in recovery_data.REGISTROS_PUBLICOS_RECUPERADOS)
    assert all(row.get("tese_resumo") for row in recovery_data.REGISTROS_PUBLICOS_RECUPERADOS)


def test_recovery_is_idempotent_and_does_not_replace_records(tmp_path, monkeypatch):
    db_path = tmp_path / "jurisprudencia.db"
    marker_path = tmp_path / ".carga-publica-recuperada-v1"
    monkeypatch.setattr(connection, "DB_PATH", db_path)
    monkeypatch.setattr(recovery_data, "DB_PATH", db_path)

    assert recovery_data.carregar_recuperacao_publica() == len(
        recovery_data.REGISTROS_PUBLICOS_RECUPERADOS
    )
    assert len(listar_decisoes()) == len(recovery_data.REGISTROS_PUBLICOS_RECUPERADOS)
    assert recovery_data.carregar_recuperacao_publica() == 0
    assert len(listar_decisoes()) == len(recovery_data.REGISTROS_PUBLICOS_RECUPERADOS)
    assert marker_path.exists()


def test_recovery_skips_a_nonempty_database(tmp_path, monkeypatch):
    db_path = tmp_path / "jurisprudencia.db"
    monkeypatch.setattr(connection, "DB_PATH", db_path)
    monkeypatch.setattr(recovery_data, "DB_PATH", db_path)
    connection.init_db()

    with connection.get_connection() as conn:
        conn.execute(
            """INSERT INTO decisoes
            (tribunal, tipo, identificador, titulo, ramo, status, tese_resumo)
            VALUES ('STF', 'Teste', 'local-1', 'Registro local', 'Direito Administrativo', 'Atual', 'Conteúdo local')"""
        )

    assert recovery_data.carregar_recuperacao_publica() == 0
    assert len(listar_decisoes()) == 1
    assert recovery_data._marker_path().exists()
