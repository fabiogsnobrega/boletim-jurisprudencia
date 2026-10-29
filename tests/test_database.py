"""Testes para o módulo de banco de dados e filtros."""

from database import init_db, inserir_decisao, listar_decisoes


def test_database_operations() -> None:
    init_db()
    total_antes = len(listar_decisoes())

    novo_id = inserir_decisao({
        "tribunal": "TRF1",
        "tipo": "Julgado de Turma",
        "identificador": "Teste Unitario 01",
        "titulo": "Decisao de Teste",
        "ramo": "Direito Militar",
        "status": "Transitado em Julgado",
        "em_alerta": 0,
        "prazo_alerta": "Concluído",
        "relator": "Relator Teste",
        "orgao_julgador": "Primeira Turma",
        "processo_origem": "0000000-00.2026.4.01.0000",
        "data_evento": "28/10/2026",
        "tese_resumo": "Tese de teste para validacao do sistema.",
        "conclusao_comentarios": "Comentarios de teste.",
        "link_oficial": "https://teste.jus.br",
    })

    assert novo_id > 0
    total_depois = len(listar_decisoes())
    assert total_depois == total_antes + 1

    # Testa filtro por tribunal
    filtradas = listar_decisoes(tribunal="TRF1")
    assert any(d["identificador"] == "Teste Unitario 01" for d in filtradas)

    # Testa busca por palavra-chave
    busca = listar_decisoes(busca="validacao do sistema")
    assert len(busca) >= 1

    # Testa atualização de prazo/verificação
    from database import atualizar_verificacao, excluir_decisao
    atualizou = atualizar_verificacao(novo_id, nova_data_limite="2026-12-31")
    assert atualizou is True

    # Testa exclusão da decisão
    excluiu = excluir_decisao(novo_id)
    assert excluiu is True
    assert len(listar_decisoes()) == total_antes
