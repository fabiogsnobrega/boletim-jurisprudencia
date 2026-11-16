"""Cobertura do modo de demonstração para instalações sem dados."""

from demo_data import criar_decisoes_demo, filtrar_decisoes_demo
from modules.noticias import _link_http_seguro, _texto_html


def test_exemplos_demo_sao_identificados_e_nao_parecem_julgados_reais():
    decisoes = criar_decisoes_demo()

    assert len(decisoes) == 3
    assert all("EXEMPLO FICTÍCIO" in decisao["titulo"] for decisao in decisoes)
    assert all(decisao["processo_origem"] == "Sem processo real" for decisao in decisoes)
    assert all(decisao["link_oficial"] is None for decisao in decisoes)
    assert sum(bool(decisao["em_alerta"]) for decisao in decisoes) == 1


def test_filtros_do_demo_respeitam_tribunal_ramo_e_busca():
    decisoes = criar_decisoes_demo()

    assert [d["identificador"] for d in filtrar_decisoes_demo(decisoes, tribunal="TRF1")] == ["EXEMPLO-001"]
    assert [d["identificador"] for d in filtrar_decisoes_demo(decisoes, ramo="Militar")] == ["EXEMPLO-003"]
    assert [d["identificador"] for d in filtrar_decisoes_demo(decisoes, busca="desenvolvimento")] == ["EXEMPLO-002"]


def test_valores_de_usuario_sao_escapados_antes_de_inserir_em_html():
    assert _texto_html('<img src=x onerror="alert(1)">') == "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
    assert _link_http_seguro("javascript:alert(1)") == ""
    assert _link_http_seguro("https://exemplo.org/decisao?a=1&b=2") == "https://exemplo.org/decisao?a=1&amp;b=2"
