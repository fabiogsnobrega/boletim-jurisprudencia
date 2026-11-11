"""Testes para o extrator de boletins de jurisprudência."""

from extractor import eh_relevante_adm_militar, extrair_decisoes_de_texto


def test_filtro_relevancia() -> None:
    assert eh_relevante_adm_militar("Decisão sobre servidor público e concurso")
    assert eh_relevante_adm_militar("Pensão por morte de militar na caserna")
    assert not eh_relevante_adm_militar("Tráfico de drogas e direito penal comum")


def test_extrair_decisoes_snippet() -> None:
    texto_amostra = """
    BOLETIM INFORMATIVO JURISPRUDENCIAL TRF1
    TEMA 1444 STJ
    Questão submetida a julgamento: Definir se é possível a expedição de precatório ou RPV com bloqueio antes do trânsito.
    Comentários: Suspensão nacional em curso.
    """
    decisoes = extrair_decisoes_de_texto(texto_amostra, tribunal_padrao="STJ")
    assert len(decisoes) >= 1
    assert "1444" in decisoes[0]["identificador"]
    assert decisoes[0]["em_alerta"] == 1
    assert decisoes[0]["data_limite_verificacao"] is not None
    assert decisoes[0]["avisos_validacao"]
