"""Compatibilidade para código antigo; a pipeline agora vive em ``agents``."""

from agents.classifier import ClassificadorJurisprudenciaML, PESOS_TEMATICOS, classificador_global
from agents.decision_parser import detectar_tribunal, eh_relevante_adm_militar, extrair_decisoes_de_texto
from agents.pdf_reader import extrair_texto_pdf

__all__ = [
    "ClassificadorJurisprudenciaML",
    "PESOS_TEMATICOS",
    "classificador_global",
    "detectar_tribunal",
    "eh_relevante_adm_militar",
    "extrair_decisoes_de_texto",
    "extrair_texto_pdf",
]
