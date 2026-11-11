from services.audit import registrar_evento

from database import listar_eventos_auditoria


def test_auditoria_registra_metadados_sem_conteudo_sensivel():
    evento_id = registrar_evento(
        "revisor@example.org",
        "aceitar",
        "candidato",
        42,
        {"origem": "PDF oficial"},
    )

    eventos = listar_eventos_auditoria()

    assert evento_id > 0
    assert eventos[0]["ator"] == "revisor@example.org"
    assert eventos[0]["acao"] == "aceitar"
    assert eventos[0]["recurso_id"] == "42"
    assert "PDF oficial" in eventos[0]["detalhes_json"]
