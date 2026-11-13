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


def test_responsavel_mes_ciclo() -> None:
    from datetime import date
    from database import calcular_ciclo_mensal, salvar_responsavel_mes, verificar_status_responsavel

    ini, fim = calcular_ciclo_mensal(date(2026, 10, 15))
    assert ini == "2026-10-02"
    assert fim == "2026-11-01"

    ini_dia1, fim_dia1 = calcular_ciclo_mensal(date(2026, 11, 1))
    assert ini_dia1 == "2026-10-02"
    assert fim_dia1 == "2026-11-01"

    # Salva e testa validação
    salvar_responsavel_mes("teste@marcosinacio.adv.br", "1234", ini, fim)
    valido, _, resp = verificar_status_responsavel()
    assert resp is not None
    assert resp["email"] == "teste@marcosinacio.adv.br"


def test_responsavel_nao_aceita_senha_vazia():
    import pytest
    from database import salvar_responsavel_mes

    with pytest.raises(ValueError, match="não pode ficar vazia"):
        salvar_responsavel_mes("sem-senha@example.org", "  ", "2026-11-02", "2026-12-01")


def test_hash_e_duplicatas() -> None:
    from database import calcular_hash_decisao, excluir_decisao, inserir_decisao

    decisao = {
        "tribunal": "TRF5",
        "tipo": "Julgado de Turma",
        "identificador": "Teste Hash 01",
        "titulo": "Decisao para Teste de Hash e Duplicatas",
        "ramo": "Direito Administrativo / Servidor Público",
        "status": "Transitado em Julgado",
        "processo_origem": "0800000-00.2026.4.05.0000",
        "tese_resumo": "Tese com hash para garantia de unicidade.",
    }

    hash_val = calcular_hash_decisao(decisao)
    assert len(hash_val) == 64  # SHA-256 hexdigest

    id1 = inserir_decisao(decisao, usuario="tester@marcosinacio.adv.br", origem="boletim_teste.pdf")
    assert id1 > 0

    # Inserção duplicada deve ser detectada e retornar 0
    id2 = inserir_decisao(decisao, usuario="tester@marcosinacio.adv.br", origem="boletim_teste.pdf")
    assert id2 == 0

    excluir_decisao(id1)


def test_acoes_em_lote_revisao() -> None:
    from database import (
        aceitar_candidatos_em_lote,
        adicionar_a_fila_revisao,
        excluir_decisao,
        listar_fila_revisao,
        rejeitar_candidatos_em_lote,
    )

    c1 = {
        "tribunal": "TRF1",
        "tipo": "Julgado",
        "identificador": "LOTE-001",
        "titulo": "Item Lote 1",
        "ramo": "Direito Militar",
        "status": "Transitado em Julgado",
        "tese_resumo": "Tese lote 1",
    }
    c2 = {
        "tribunal": "TRF1",
        "tipo": "Julgado",
        "identificador": "LOTE-002",
        "titulo": "Item Lote 2",
        "ramo": "Direito Militar",
        "status": "Transitado em Julgado",
        "tese_resumo": "Tese lote 2",
    }
    c3 = {
        "tribunal": "TRF1",
        "tipo": "Julgado",
        "identificador": "LOTE-003",
        "titulo": "Item Lote 3",
        "ramo": "Direito Militar",
        "status": "Transitado em Julgado",
        "tese_resumo": "Tese lote 3",
    }

    id_f1 = adicionar_a_fila_revisao(c1, criado_por="teste@lote.com")
    id_f2 = adicionar_a_fila_revisao(c2, criado_por="teste@lote.com")
    id_f3 = adicionar_a_fila_revisao(c3, criado_por="teste@lote.com")

    # Aceita c1 e c2 em lote
    aceitos, dups = aceitar_candidatos_em_lote([id_f1, id_f2], revisor="revisor@lote.com")
    assert aceitos == 2
    assert dups == 0

    # Rejeita c3 em lote
    rejeitados = rejeitar_candidatos_em_lote([id_f3], revisor="revisor@lote.com")
    assert rejeitados == 1

    # Limpeza no banco oficial
    from database import listar_decisoes
    todas = listar_decisoes()
    for d in todas:
        if d["identificador"] in ("LOTE-001", "LOTE-002"):
            excluir_decisao(d["id"])


def test_aprovacao_individual_de_duplicata_tem_estado_consistente_e_auditoria():
    from database import (
        aceitar_candidato,
        adicionar_a_fila_revisao,
        inserir_decisao,
        listar_eventos_auditoria,
        listar_fila_revisao,
    )

    decisao = {
        "tribunal": "TRF1", "tipo": "Julgado", "identificador": "DUP-001",
        "titulo": "Decisão duplicada", "ramo": "Direito Militar",
        "status": "Transitado em Julgado", "tese_resumo": "Conteúdo duplicado de teste.",
        "texto_original": "Conteúdo original igual para produzir o mesmo hash.",
    }
    assert inserir_decisao(decisao, usuario="teste") > 0
    candidato_id = adicionar_a_fila_revisao(decisao, criado_por="teste")

    assert aceitar_candidato(candidato_id, None, "revisor") is False
    fila = listar_fila_revisao(status="rejeitada")
    assert any(item["id"] == candidato_id and "Duplicata" in item["comentario_usuario"] for item in fila)
    assert any(evento["acao"] == "insercao_duplicada" and evento["recurso_id"] == str(candidato_id)
               for evento in listar_eventos_auditoria())


def test_exclusao_e_evento_de_auditoria_sao_gravados_juntos():
    from database import inserir_decisao, excluir_decisao, listar_eventos_auditoria

    decision_id = inserir_decisao({
        "tribunal": "TRF1", "tipo": "Julgado", "identificador": "AUD-DELETE",
        "titulo": "Auditoria de exclusão", "ramo": "Direito Militar",
        "status": "Transitado em Julgado", "tese_resumo": "Teste de auditoria.",
    }, usuario="auditor")
    assert excluir_decisao(decision_id, ator="auditor")
    assert any(evento["acao"] == "excluir" and evento["recurso_id"] == str(decision_id)
               for evento in listar_eventos_auditoria())


def test_falha_na_auditoria_reverte_a_exclusao(monkeypatch):
    import pytest
    import database.repositories as repositories
    from database import inserir_decisao, listar_decisoes

    decision_id = inserir_decisao({
        "tribunal": "TRF1", "tipo": "Julgado", "identificador": "AUD-ROLLBACK",
        "titulo": "Rollback de exclusão", "ramo": "Direito Militar",
        "status": "Transitado em Julgado", "tese_resumo": "Teste de transação.",
    })

    def falhar_auditoria(*_args, **_kwargs):
        raise RuntimeError("falha simulada da auditoria")

    monkeypatch.setattr(repositories, "_registrar_evento_conn", falhar_auditoria)
    with pytest.raises(RuntimeError, match="falha simulada"):
        repositories.excluir_decisao(decision_id, ator="auditor")
    assert any(decisao["id"] == decision_id for decisao in listar_decisoes())
