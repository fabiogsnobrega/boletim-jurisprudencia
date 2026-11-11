"""Segmentação de texto de boletins em candidatos a decisão."""

from .parser import detectar_tribunal, eh_relevante_adm_militar, extrair_decisoes_de_texto

__all__ = ["detectar_tribunal", "eh_relevante_adm_militar", "extrair_decisoes_de_texto"]
