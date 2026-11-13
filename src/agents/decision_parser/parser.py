"""Segmentação e normalização de decisões a partir do texto extraído."""

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from agents.classifier import (
    ClassificadorJurisprudenciaML,
    PESOS_TEMATICOS,
    classificador_global,
)
from agents.validator import validar_candidato


def detectar_tribunal(texto: str) -> str:
    """Identifica o tribunal de origem predominante no boletim."""
    texto_upper = texto.upper()
    if "TRF1" in texto_upper or "1ª REGIÃO" in texto_upper or "PRIMEIRA REGIÃO" in texto_upper:
        return "TRF1"
    if "TRU5" in texto_upper or re.search(r"\bTRU\b", texto_upper) or "TURMA REGIONAL DE UNIFORMIZAÇÃO" in texto_upper:
        return "TRU5"
    if "TRF5" in texto_upper or "5ª REGIÃO" in texto_upper or "QUINTA REGIÃO" in texto_upper:
        return "TRF5"
    if "TNU" in texto_upper or "TURMA NACIONAL DE UNIFORMIZAÇÃO" in texto_upper:
        return "TNU"
    if "STJ" in texto_upper or "SUPERIOR TRIBUNAL DE JUSTIÇA" in texto_upper:
        return "STJ"
    if "STF" in texto_upper or "SUPREMO TRIBUNAL" in texto_upper:
        return "STF"
    return "Outros"


def eh_relevante_adm_militar(texto: str) -> bool:
    """Exige indicadores de vínculo público, carreira/concurso ou matéria militar."""
    texto_lower = texto.lower()
    termos_militares = PESOS_TEMATICOS["Direito Militar"]
    termos_concurso = (
        "concurso público", "concurso para", "edital de concurso", "edital do concurso",
        "vagas imediatas", "cadastro de reserva", "lista de espera", "investigação social",
        "eliminação de candidato", "direito subjetivo à nomeação", "aprovado em concurso",
        "aprovada em concurso", "nomeação em concurso",
    )
    termos_servidor = (
        "servidor", "servidora", "servidores", "empregado público", "empregada pública",
        "empregados públicos", "cargo público", "cargo efetivo", "regime estatutário",
        "lei 8.112", "progressão funcional", "remuneração de servidor",
        "gratificação de servidor", "pensão de servidor", "aposentadoria de servidor",
        "aposentadoria por invalidez de servidor", "reversão de aposentadoria de servidor",
        "magistério público", "professor da rede pública", "professores da rede pública",
        "bônus de eficiência", "bepata", "geac", "reajuste de 28,86%",
    )
    termos_administracao_publica = (
        "precatório", "precatórios", "rpv", "requisição de pequeno valor", "fazenda pública",
    )
    if any(termo in texto_lower for termo in termos_militares):
        return True
    if any(termo in texto_lower for termo in termos_concurso):
        return True
    if any(termo in texto_lower for termo in termos_servidor):
        return True
    if any(termo in texto_lower for termo in termos_administracao_publica):
        return True
    # Benefício previdenciário ou pedido administrativo isolado não demonstra vínculo público.
    return False


def extrair_decisoes_de_texto(
    texto_bruto: str,
    tribunal_padrao: Optional[str] = None,
    apenas_adm_militar: bool = True,
) -> List[Dict[str, Any]]:
    """Analisa o texto do boletim e extrai as decisões com metadados estruturados."""
    tribunal_detectado = tribunal_padrao or detectar_tribunal(texto_bruto)
    hoje = date.today()

    # Normaliza quebras de linha e espaçamentos
    texto_limpo = re.sub(r"\r\n", "\n", texto_bruto)

    # Identifica divisões de blocos
    blocos = re.split(
        r"\n(?=(?:DECIS[AÃ]O\s*\d+|TEMA\s+\d+|BOLETIM\s+INFORMATIVO|CONTROVÉRSIA\s+\d+|RECURSO\s+ESPECIAL|\b(?:ApelRemNec|ApCiv|Ap|AC|RMS|RE|ARE|PEDILEF)\s+\d+))",
        texto_limpo,
        flags=re.IGNORECASE,
    )

    if len(blocos) <= 1:
        blocos = [b.strip() for b in re.split(r"\n\s*\n\s*\n+", texto_limpo) if b.strip()]

    decisoes_extraidas: List[Dict[str, Any]] = []

    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco or (len(bloco) < 70 and apenas_adm_militar):
            continue

        # Filtro temático
        if apenas_adm_militar and not eh_relevante_adm_militar(bloco):
            continue

        # Classificação do Ramo do Direito via Classificador
        ramo_classificado, _ = classificador_global.predizer_ramo(bloco)

        # 1. Identificador & Processo
        tema_match = re.search(r"(?:TEMA|Tema)\s*(?:STF|STJ|TNU)?\s*[:\s-]*(\d+[\.\d]*)", bloco, flags=re.IGNORECASE)
        proc_match = re.search(
            r"((?:ApelRemNec|ApCiv|ApReeNec|Ap|AC|RMS|REsp|RE|ARE|PEDILEF)\s*(?:nº|n\.º|n\.|º)?\s*[\d\.\-\/]+(?:[A-Z]{2})?)",
            bloco,
            flags=re.IGNORECASE,
        )
        cnj_match = re.search(r"(\d{7}-\d{2}\.\d{4}\.4\.\d{2}\.\d{4})", bloco)

        identificador = "Decisão Jurisprudencial"
        processo_origem = ""
        if tema_match:
            identificador = f"Tema {tema_match.group(1)}"
        elif proc_match:
            identificador = proc_match.group(1).strip()
            processo_origem = identificador
        elif cnj_match:
            identificador = cnj_match.group(1)
            processo_origem = identificador

        if not processo_origem and proc_match:
            processo_origem = proc_match.group(1).strip()
        if not processo_origem and cnj_match:
            processo_origem = cnj_match.group(1).strip()

        # 2. Título
        linhas = [l.strip() for l in bloco.split("\n") if l.strip()]
        titulo = "Decisão de Jurisprudência"
        if linhas:
            primeira_linha = linhas[0]
            primeira_linha = re.sub(
                r"^(?:DECIS[AÃ]O\s*\d+\s*[:\-]?\s*|BOLETIM.*?|TEMA\s+\d+.*?[:\s-]*|CONTROVÉRSIA\s+\d+.*?[:\s-]*)",
                "",
                primeira_linha,
                flags=re.IGNORECASE,
            ).strip()
            if primeira_linha:
                titulo = primeira_linha[:120]
            elif len(linhas) > 1:
                titulo = linhas[1][:120]

        # 3. Status, Alerta e Prazos
        transito_match = re.search(
            r"tr[âa]nsito\s+em\s+julgado(?:\s+em\s*[:\s]*(\d{2}/\d{2}/\d{4}))?",
            bloco,
            flags=re.IGNORECASE,
        )
        data_evento_match = re.search(r"(\d{2}/\d{2}/\d{4})", bloco)
        data_evento = data_evento_match.group(1) if data_evento_match else ""

        if transito_match:
            status = "Transitado em Julgado"
            em_alerta = 0
            prazo_alerta = "Concluído"
            data_limite_verificacao = None
        elif re.search(r"afetad[oa]|pendente|em julgamento|aguardando|suspens(?:[ãa]o|[oa])|incluíd[oa]\s+em pauta", bloco, re.IGNORECASE):
            status = "Em Acompanhamento / Pendente"
            em_alerta = 1
            # Data limite sugerida para verificação (30 dias)
            data_limite_dt = hoje + timedelta(days=30)
            data_limite_verificacao = data_limite_dt.strftime("%Y-%m-%d")
            prazo_alerta = f"Até {data_limite_dt.strftime('%d/%m/%Y')}"
        else:
            status = "Não identificado no documento"
            em_alerta = 0
            prazo_alerta = "Sem alerta automático"
            data_limite_verificacao = None

        # 4. Relator e Órgão
        relator_match = re.search(
            r"(?:relator\(a\)|rel\.|relator)[:\s]+(?:min\.|des\.|ministro|desembargador|juiz)?\s*([A-Za-zÀ-ÿ\s]+?)(?:,|$|\n)",
            bloco,
            flags=re.IGNORECASE,
        )
        relator = relator_match.group(1).strip() if relator_match else ""

        turma_match = re.search(
            r"(\d+ª\s+Turma|Segunda\s+Turma|Primeira\s+Turma|Pleno|Primeira\s+Seção|Tribunal\s+Pleno)",
            bloco,
            flags=re.IGNORECASE,
        )
        orgao_julgador = turma_match.group(1).strip() if turma_match else ""

        # 5. Tese / Resumo
        tese_match = re.search(
            r"(?:tese(?:\s+firmada)?|o\s+tribunal\s+fixou.*?tese|questão\s+submetida.*?julgamento)[:\s]+(.*?)(?=(?:coment[aá]rios|conclus[aã]o|resultado|$))",
            bloco,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if tese_match:
            tese_resumo = tese_match.group(1).strip()
        else:
            tese_resumo = bloco

        # 6. Comentários / Conclusão
        coment_match = re.search(r"(?:coment[aá]rios|conclus[aã]o)[:\s]+(.*?)$", bloco, flags=re.IGNORECASE | re.DOTALL)
        conclusao_comentarios = coment_match.group(1).strip() if coment_match else ""

        candidato = {
            "tribunal": tribunal_detectado,
            "tipo": "Tema Repetitivo / Repercussão Geral" if "Tema" in identificador else "Julgado de Turma",
            "identificador": identificador,
            "titulo": titulo,
            "ramo": ramo_classificado,
            "status": status,
            "em_alerta": em_alerta,
            "prazo_alerta": prazo_alerta,
            "data_limite_verificacao": data_limite_verificacao,
            "relator": relator,
            "orgao_julgador": orgao_julgador,
            "processo_origem": processo_origem,
            "data_evento": data_evento,
            "tese_resumo": tese_resumo,
            "texto_original": bloco,
            "conclusao_comentarios": conclusao_comentarios,
            "link_oficial": "",
        }
        candidato["avisos_validacao"] = validar_candidato(candidato)
        decisoes_extraidas.append(candidato)

    return decisoes_extraidas
