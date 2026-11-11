"""Testes dos componentes de leitura isolados da interface Streamlit."""

from agents.classifier import ClassificadorJurisprudenciaML
from agents.pdf_reader import reader
from agents.validator import validar_candidato


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
    assert "relevante para" in sugestao
    assert "Concurso Público" in sugestao


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
