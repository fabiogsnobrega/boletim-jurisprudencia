"""Testes dos componentes de leitura isolados da interface Streamlit."""

from agents.classifier import ClassificadorJurisprudenciaML
from agents.pdf_reader import reader
from agents.validator import validar_candidato
from extractor import detectar_tribunal, eh_relevante_adm_militar


def test_classificador_tematico_pode_ser_exercitado_isoladamente():
    classificador = ClassificadorJurisprudenciaML()

    ramo, confianca = classificador.predizer_ramo(
        "Concurso público, edital e candidata aprovada para nomeação"
    )

    assert ramo == "Direito Administrativo / Concurso Público"
    assert confianca > 0

    sugestao = classificador.sugerir_relevancia({
        "texto_original": "candidato reprovado no exame do concurso público"
    })
    assert "Matéria identificada" in sugestao
    assert "Concurso Público" in sugestao
    assert "%" not in sugestao


def test_leitor_pdf_preserva_a_ordem_das_paginas(monkeypatch):
    class Pagina:
        def __init__(self, texto):
            self.texto = texto

        def extract_text(self):
            return self.texto

    class LeitorFalso:
        def __init__(self, _arquivo):
            self.pages = [Pagina("Página um"), Pagina("Página dois")]

    monkeypatch.setattr(reader, "PdfReader", LeitorFalso)

    paginas = reader.extrair_texto_pdf_por_pagina(b"pdf de teste")
    assert len(paginas) == 2
    assert paginas[0] == (1, "Página um", False)
    assert paginas[1] == (2, "Página dois", False)
    assert reader.extrair_texto_pdf(b"pdf de teste") == "Página um\n\nPágina dois"

    from agents.pdf_reader.ocr import ocr_pagina
    assert ocr_pagina(b"imagem") is None


def test_validador_avisa_sem_descartar_o_candidato():
    candidato = {
        "identificador": "Decisão Jurisprudencial",
        "titulo": "Decisão de Jurisprudência",
        "processo_origem": "",
        "data_evento": "",
        "status": "Não identificado no documento",
        "em_alerta": 0,
        "texto_original": "Trecho original mantido.",
    }

    avisos = validar_candidato(candidato)

    assert len(avisos) >= 4
    assert candidato["texto_original"] == "Trecho original mantido."


def test_tribunal_usa_nome_especifico_e_limites_de_palavra():
    assert detectar_tribunal("Turma Regional de Uniformização da 5ª Região") == "TRU5"
    assert detectar_tribunal("Turma Nacional de Uniformização") == "TNU"
    assert detectar_tribunal("A estrutura administrativa foi revista") == "Outros"
    assert detectar_tribunal("TRU5") == "TRU5"


def test_filtro_relevancia_exige_vinculo_publico_ou_materia_militar():
    aposentado_inss = (
        "Aposentado do INSS teve benefício bloqueado em consequência de processo penal. "
        "Apresentou requerimento administrativo para desbloqueio."
    )
    assert not eh_relevante_adm_militar(aposentado_inss)
    assert not eh_relevante_adm_militar("Candidato requereu administrativamente o desbloqueio de benefício previdenciário.")
    assert eh_relevante_adm_militar("Servidor público aposentado pede revisão de aposentadoria por invalidez.")
    assert eh_relevante_adm_militar("Candidata aprovada em concurso público foi preterida na nomeação.")
    assert eh_relevante_adm_militar("Pensão militar de dependente de oficial das Forças Armadas.")


def test_chamada_gemini_so_ocorre_no_clique_explicito():
    import ast
    from pathlib import Path

    modulo = ast.parse((Path(__file__).parents[1] / "src" / "modules" / "revisao.py").read_text(encoding="utf-8"))
    chamadas = [node for node in ast.walk(modulo)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "gerar_analise_inteligente"]
    assert len(chamadas) == 1
    # O fluxo da chamada fica sob a condição do botão de ação; só renderizar a fila não chama a IA.
    botoes_com_chamada = [node for node in ast.walk(modulo)
                          if isinstance(node, ast.If)
                          and isinstance(node.test, ast.Call)
                          and isinstance(node.test.func, ast.Attribute)
                          and isinstance(node.test.func.value, ast.Name)
                          and node.test.func.value.id == "st"
                          and node.test.func.attr == "button"
                          and any(isinstance(arg, ast.Constant) and arg.value == "Gerar análise sugerida"
                                  for arg in node.test.args)
                          and any(chamada in ast.walk(statement) for statement in node.body for chamada in chamadas)]
    assert botoes_com_chamada


def test_gemini_usa_modelo_configurado_e_chave_no_header(monkeypatch):
    import agents.ai_analyst.analyst as analyst

    chamada = {}

    class Resposta:
        status_code = 200

        @staticmethod
        def json():
            return {"candidates": [{"content": {"parts": [{"text": "Resumo do Gemini"}]}}]}

    monkeypatch.setattr(analyst, "obter_chave_gemini", lambda: "teste-chave")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-de-teste")

    def postar(url, **kwargs):
        chamada["url"] = url
        chamada.update(kwargs)
        return Resposta()

    monkeypatch.setattr(analyst.requests, "post", postar)
    texto = analyst.gerar_analise_inteligente({"texto_original": "Decisão para análise."}, usar_ia=True)
    assert "Resumo do Gemini" in texto
    assert chamada["url"].endswith("/models/modelo-de-teste:generateContent")
    assert chamada["headers"]["x-goog-api-key"] == "teste-chave"
    assert "key=" not in chamada["url"]


def test_ai_analyst_gera_explicacao_e_publico_alvo():
    from agents.ai_analyst.analyst import extrair_hashtags_tematicas, gerar_analise_inteligente

    dados_concurso = {
        "tribunal": "TRF1",
        "identificador": "AC 0001234-56.2026.4.01.3400",
        "ramo": "Direito Administrativo / Concurso Público",
        "texto_original": "Candidato aprovado em concurso público com preterição na nomeação de vaga prevista no edital.",
    }

    tags = extrair_hashtags_tematicas(dados_concurso["texto_original"], dados_concurso["ramo"])
    assert "#ConcursoPublico" in tags or "#Nomeacao" in tags

    analise = gerar_analise_inteligente(dados_concurso, usar_ia=False)
    assert "Explicação da Decisão" in analise
    assert "Público-Alvo e Oportunidades" in analise
    assert "Candidatos" in analise
