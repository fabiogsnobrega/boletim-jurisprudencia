"""Formatação compartilhada dos prazos de acompanhamento."""

from datetime import date, datetime


def calcular_prazo(data_limite_str: str) -> tuple[int, str, str]:
    """Calcula os dias restantes e escolhe o rótulo visual do prazo."""
    hoje = date.today()
    try:
        limite = datetime.strptime(data_limite_str, "%Y-%m-%d").date()
        dias = (limite - hoje).days
        data_formatada = limite.strftime("%d/%m/%Y")
        if dias < 0:
            return dias, f"⚠️ VENCIDO há {abs(dias)} dia(s) (em {data_formatada})", "badge-alerta-vencido"
        if dias == 0:
            return dias, f"🔔 VENCE HOJE! (em {data_formatada})", "badge-alerta-hoje"
        return dias, f"⏱️ Faltam {dias} dia(s) para verificar (até {data_formatada})", "badge-alerta-em-dia"
    except Exception:
        return 0, f"⏱️ Prazo: {data_limite_str}", "badge-alerta-em-dia"
