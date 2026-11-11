"""Estruturas de dados compartilhadas pela extração e persistência."""

from typing import TypedDict


class DecisionData(TypedDict, total=False):
    """Campos conhecidos de um candidato ou decisão; dados extraídos são parciais."""

    id: int
    tribunal: str
    tipo: str
    identificador: str
    titulo: str
    ramo: str
    status: str
    em_alerta: int
    prazo_alerta: str
    data_limite_verificacao: str | None
    relator: str
    orgao_julgador: str
    processo_origem: str
    data_evento: str
    tese_resumo: str
    texto_original: str
    conclusao_comentarios: str
    link_oficial: str
    avisos_validacao: list[str]
