"""Serviço de auditoria das ações administrativas e de revisão."""

from typing import Any, Dict, Optional

from database import registrar_evento_auditoria


def registrar_evento(
    ator: Optional[str],
    acao: str,
    recurso: str,
    recurso_id: Optional[str | int] = None,
    detalhes: Optional[Dict[str, Any]] = None,
) -> int:
    """Persiste metadados da ação; evita guardar comentários ou texto jurídico."""
    return registrar_evento_auditoria(ator, acao, recurso, str(recurso_id) if recurso_id is not None else None, detalhes)
