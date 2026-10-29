"""Módulo para leitura e extração inteligente de decisões de boletins em PDF ou texto."""

import io
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from pypdf import PdfReader

# Termos-chave de relevância para Direito Administrativo e Militar
TERMOS_ADMINISTRATIVO_MILITAR = [
    "administrativ", "militar", "servidor", "concurso", "aposentad",
    "pensao", "pensão", "remunera", "vencimento", "geac", "bepata",
    "reajuste", "pad", "demiss", "licen", "ex-combatente", "magisterio",
    "magistério", "policial", "precatório", "precatorio", "rpv",
    "fazenda pública", "fazenda publica", "fundo de direito", "invalidez",
    "estatuto dos militares", "paridade", "quadro de pessoal"
]


def extrair_texto_pdf(arquivo_bytes: bytes) -> str:
    """Lê todas as páginas de um PDF e retorna o texto completo concatenado."""
    leitor = PdfReader(io.BytesIO(arquivo_bytes))
    paginas_texto = []
    for idx, pagina in enumerate(leitor.pages):
        texto = pagina.extract_text() or ""
        paginas_texto.append(texto)
    return "\n\n".join(paginas_texto)


def detectar_tribunal(texto: str) -> str:
    """Identifica o tribunal de origem predominante no boletim."""
    texto_upper = texto.upper()
    if "TRF1" in texto_upper or "1ª REGIÃO" in texto_upper or "PRIMEIRA REGIÃO" in texto_upper:
        return "TRF1"
    if "TRF5" in texto_upper or "5ª REGIÃO" in texto_upper or "QUINTA REGIÃO" in texto_upper:
        return "TRF5"
    if "TNU" in texto_upper or "UNIFORMIZAÇÃO" in texto_upper:
        return "TNU"
    if "STJ" in texto_upper or "SUPERIOR TRIBUNAL DE JUSTIÇA" in texto_upper:
        return "STJ"
    if "STF" in texto_upper or "SUPREMO TRIBUNAL" in texto_upper:
        return "STF"
    return "Outros"


def eh_relevante_adm_militar(texto: str) -> bool:
    """Verifica se o trecho possui termos relacionados a Direito Administrativo ou Militar."""
    texto_lower = texto.lower()
    return any(termo in texto_lower for termo in TERMOS_ADMINISTRATIVO_MILITAR)


def extrair_decisoes_de_texto(
    texto_bruto: str,
    tribunal_padrao: Optional[str] = None,
    apenas_adm_militar: bool = True,
) -> List[Dict[str, Any]]:
    """Analisa o texto do boletim e extrai as decisões individuais com metadados."""
    tribunal_detectado = tribunal_padrao or detectar_tribunal(texto_bruto)
    hoje = date.today()

    # Normaliza quebras de linha e espaçamentos
    texto_limpo = re.sub(r"\r\n", "\n", texto_bruto)
    
    # Divide o texto em blocos de decisões potenciais
    # Reconhece quebras clássicas: "Tema \d+", cabeçalhos de decisões, processos com parênteses
    blocos = re.split(r"\n(?=(?:TEMA\s+\d+|BOLETIM\s+INFORMATIVO|CONTROVÉRSIA\s+\d+|RECURSO\s+ESPECIAL|\b(?:ApelRemNec|ApCiv|Ap|AC|RMS|RE|ARE|PEDILEF)\s+\d+))", texto_limpo, flags=re.IGNORECASE)
    
    # Se a quebra não produziu muitos blocos, tenta dividir por linhas em branco duplas com tamanho mínimo
    if len(blocos) <= 1:
        blocos = [b.strip() for b in re.split(r"\n\s*\n\s*\n+", texto_limpo) if len(b.strip()) > 100]

    decisoes_extraidas: List[Dict[str, Any]] = []

    for bloco in blocos:
        bloco = bloco.strip()
        if len(bloco) < 80:
            continue

        # Filtro temático (Administrativo / Militar)
        if apenas_adm_militar and not eh_relevante_adm_militar(bloco):
            continue

        # 1. Identificador & Processo
        # Busca Tema
        tema_match = re.search(r"(?:TEMA|Tema)\s*(?:STF|STJ|TNU)?\s*[:\s-]*(\d+[\.\d]*)", bloco, flags=re.IGNORECASE)
        # Busca Processo (PJe, CNJ, REsp, etc.)
        proc_match = re.search(
            r"((?:ApelRemNec|ApCiv|ApReeNec|Ap|AC|RMS|REsp|RE|ARE|PEDILEF)\s*(?:nº|n\.º|n\.|º)?\s*[\d\.\-\/]+(?:[A-Z]{2})?)",
            bloco,
            flags=re.IGNORECASE,
        )
        cnj_match = re.search(r"(\d{7}-\d{2}\.\d{4}\.4\.\d{2}\.\d{4})", bloco)

        identificador = "Decisão / Julgado"
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

        # 2. Ramo do Direito
        ramo = "Direito Administrativo"
        if "militar" in bloco.lower() or "caserna" in bloco.lower() or "ex-combatente" in bloco.lower():
            ramo = "Direito Militar"
        elif "concurso" in bloco.lower():
            ramo = "Direito Administrativo / Concurso Público"
        elif "servidor" in bloco.lower():
            ramo = "Direito Administrativo / Servidor Público"
        elif "previdenci" in bloco.lower():
            ramo = "Direito Administrativo / Previdenciário"

        # 3. Título / Cabeçalho
        linhas = [l.strip() for l in bloco.split("\n") if l.strip()]
        titulo = "Decisão de Jurisprudência"
        if linhas:
            primeira_linha = linhas[0]
            # Remove prefixos comuns do título
            primeira_linha = re.sub(r"^(?:BOLETIM.*?|TEMA\s+\d+.*?[:\s-]*|CONTROVÉRSIA\s+\d+.*?[:\s-]*)", "", primeira_linha, flags=re.IGNORECASE).strip()
            if primeira_linha:
                titulo = primeira_linha[:120]
            elif len(linhas) > 1:
                titulo = linhas[1][:120]

        # 4. Status, Alerta e Prazos
        # Verifica se houve trânsito em julgado
        transito_match = re.search(r"tr[âa]nsito\s+em\s+julgado(?:\s+em\s*[:\s]*(\d{2}/\d{2}/\d{4}))?", bloco, flags=re.IGNORECASE)
        data_evento_match = re.search(r"(\d{2}/\d{2}/\d{4})", bloco)

        data_evento = data_evento_match.group(1) if data_evento_match else hoje.strftime("%d/%m/%Y")
        
        if transito_match:
            status = "Transitado em Julgado"
            em_alerta = 0
            prazo_alerta = "Concluído"
            data_limite_verificacao = None
        else:
            # Não teve trânsito -> Painel de alerta com prazo sugerido
            status = "Em Acompanhamento / Pendente"
            em_alerta = 1
            # Sugere nova verificação em 20 dias
            data_limite_dt = hoje + timedelta(days=20)
            data_limite_verificacao = data_limite_dt.strftime("%Y-%m-%d")
            prazo_alerta = f"20 dias (até {data_limite_dt.strftime('%d/%m/%Y')})"

        # 5. Relator e Órgão
        relator_match = re.search(r"(?:relator\(a\)|rel\.|relator)[:\s]+(?:min\.|des\.|ministro|desembargador|juiz)?\s*([A-Za-zÀ-ÿ\s]+?)(?:,|$|\n)", bloco, flags=re.IGNORECASE)
        relator = relator_match.group(1).strip() if relator_match else ""

        turma_match = re.search(r"(\d+ª\s+Turma|Segunda\s+Turma|Primeira\s+Turma|Pleno|Primeira\s+Seção|Tribunal\s+Pleno)", bloco, flags=re.IGNORECASE)
        orgao_julgador = turma_match.group(1).strip() if turma_match else ""

        # 6. Tese / Resumo
        tese_match = re.search(r"(?:tese(?:\s+firmada)?|o\s+tribunal\s+fixou.*?tese|questão\s+submetida.*? julgamento)[:\s]+(.*?)(?=(?:coment[aá]rios|conclus[aã]o|resultado|$))", bloco, flags=re.IGNORECASE | re.DOTALL)
        if tese_match:
            tese_resumo = tese_match.group(1).strip()
        else:
            # Pega o corpo do texto
            tese_resumo = bloco[:500] + ("..." if len(bloco) > 500 else "")

        # 7. Comentários / Conclusão
        coment_match = re.search(r"(?:coment[aá]rios|conclus[aã]o)[:\s]+(.*?)$", bloco, flags=re.IGNORECASE | re.DOTALL)
        conclusao_comentarios = coment_match.group(1).strip() if coment_match else ""

        decisoes_extraidas.append({
            "tribunal": tribunal_detectado,
            "tipo": "Tema Repetitivo / Repercussão Geral" if "Tema" in identificador else "Julgado de Turma",
            "identificador": identificador,
            "titulo": titulo,
            "ramo": ramo,
            "status": status,
            "em_alerta": em_alerta,
            "prazo_alerta": prazo_alerta,
            "data_limite_verificacao": data_limite_verificacao,
            "relator": relator,
            "orgao_julgador": orgao_julgador,
            "processo_origem": processo_origem,
            "data_evento": data_evento,
            "tese_resumo": tese_resumo,
            "conclusao_comentarios": conclusao_comentarios,
            "link_oficial": "",
        })

    return decisoes_extraidas
