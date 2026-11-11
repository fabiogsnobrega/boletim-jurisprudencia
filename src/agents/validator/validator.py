"""Verificações leves para orientar a conferência humana dos candidatos."""


def validar_candidato(dados: dict) -> list[str]:
    """Retorna avisos explicáveis; nunca remove nem corrige conteúdo original."""
    avisos = []

    if not str(dados.get("texto_original") or "").strip():
        avisos.append("O texto original não foi preservado; confira a fonte antes de aceitar.")
    if dados.get("identificador") == "Decisão Jurisprudencial":
        avisos.append("O identificador do processo ou tema não foi reconhecido automaticamente.")
    if dados.get("titulo") == "Decisão de Jurisprudência":
        avisos.append("O título não foi reconhecido automaticamente.")
    if not str(dados.get("processo_origem") or "").strip():
        avisos.append("Não foi identificado um número de processo de origem.")
    if not str(dados.get("data_evento") or "").strip():
        avisos.append("Não foi identificada uma data do evento.")
    if dados.get("status") == "Não identificado no documento":
        avisos.append("A situação processual não foi identificada; nenhum prazo automático foi criado.")
    if dados.get("em_alerta") and not dados.get("data_limite_verificacao"):
        avisos.append("Há acompanhamento sugerido sem data limite de verificação.")

    return avisos
