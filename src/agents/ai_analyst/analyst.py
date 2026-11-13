"""Agente de Análise Inteligente de Decisões com Google Gemini e Fallback Heurístico."""

import json
import os
import re
from typing import Dict, List, Optional
import requests

try:
    import streamlit as st
except ImportError:
    st = None


def extrair_hashtags_tematicas(texto: str, ramo: str = "") -> List[str]:
    """Gera hashtags padronizadas com base nos termos-chave da decisão."""
    tags = set()
    ramo_lower = (ramo or "").lower()
    texto_lower = (texto or "").lower()

    if "militar" in ramo_lower or "militar" in texto_lower:
        tags.add("#DireitoMilitar")
    if "concurso" in ramo_lower or "concurso" in texto_lower:
        tags.add("#ConcursoPublico")
    if "servidor" in ramo_lower or "servidor" in texto_lower:
        tags.add("#ServidorPublico")
    if "precatório" in texto_lower or "rpv" in texto_lower:
        tags.add("#Precatorios")
    if "pensão" in texto_lower:
        tags.add("#PensaoMilitar" if "militar" in tags else "#PensaoPorMorte")
    if "reajuste" in texto_lower or "28,86" in texto_lower:
        tags.add("#ReajusteSalarial")
    if "dano moral" in texto_lower or "responsabilidade civil" in texto_lower:
        tags.add("#ResponsabilidadeCivil")
    if "nomeação" in texto_lower or "posse" in texto_lower:
        tags.add("#Nomeacao")
    if "licença" in texto_lower:
        tags.add("#LicencaPremio")

    if not tags:
        tags.add("#DireitoAdministrativo")

    return sorted(list(tags))


def obter_chave_gemini() -> Optional[str]:
    """Recupera a chave de API do Gemini das variáveis de ambiente ou secrets do Streamlit."""
    chave = os.environ.get("GEMINI_API_KEY")
    if chave:
        return chave.strip()
    if st is not None:
        try:
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                return str(st.secrets["GEMINI_API_KEY"]).strip()
        except Exception:
            pass
    return None


def gerar_analise_inteligente(dados: Dict[str, any], usar_ia: bool = True) -> str:
    """
    Gera uma análise explicando a decisão e sugerindo o público-alvo para captação.
    Se a chave do Google Gemini estiver configurada, realiza a consulta à IA;
    caso contrário, utiliza um motor de regras heurístico direcionado.
    """
    texto = str(dados.get("texto_original") or dados.get("tese_resumo") or "").strip()
    if not texto:
        return "Decisão sem texto suficiente para análise."

    tribunal = dados.get("tribunal", "Tribunal")
    identificador = dados.get("identificador", "")
    ramo = dados.get("ramo", "")
    tags = extrair_hashtags_tematicas(texto, ramo)
    tags_str = " ".join(tags)

    chave_api = obter_chave_gemini() if usar_ia else None
    aviso_ia = ""

    if chave_api:
        try:
            modelo = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
            prompt = (
                "Você é um consultor jurídico sênior e estrategista de captação de clientes para escritórios de advocacia.\n"
                f"Analise a decisão judicial abaixo do {tribunal} ({identificador}):\n\n"
                f"--- CONTEÚDO DA DECISÃO ---\n{texto[:4000]}\n---------------------------\n\n"
                "Retorne uma resposta estritamente estruturada nestes 2 pontos:\n"
                "📌 Explicação da Decisão: [Resuma de forma direta e prática em 2 ou 3 frases o que foi decidido e seu impacto].\n\n"
                "🎯 Público-Alvo e Oportunidades: [Identifique com precisão qual categoria profissional, grupo ou público pode ser beneficiado e como o escritório pode abordar esse nicho para ajuizar ações]."
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600},
            }
            resp = requests.post(url, json=payload, headers={"x-goog-api-key": chave_api}, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                candidatos = data.get("candidates", [])
                if candidatos:
                    texto_ia = candidatos[0]["content"]["parts"][0]["text"].strip()
                    return f"{texto_ia}\n\n🏷️ Temas: {tags_str}"
            aviso_ia = "A análise do Gemini não retornou uma resposta utilizável; exibindo sugestão local."
        except Exception:
            aviso_ia = "Não foi possível obter a análise do Gemini; exibindo sugestão local."
    elif usar_ia:
        aviso_ia = "Chave Gemini não configurada; exibindo sugestão local sem transmitir o texto."

    # Heurística avançada quando não há IA disponível ou offline
    conteudo_limpo = " ".join(texto.split())
    conteudo_limpo = re.sub(r"^Boletim Informativo de Jurisprudência\s*[•·-]?\s*\d*\s*", "", conteudo_limpo, flags=re.IGNORECASE)
    frases = re.split(r"(?<=[.!?])\s+", conteudo_limpo)
    resumo = " ".join(frases[:2]).strip()
    if len(resumo) > 300:
        resumo = resumo[:297].rsplit(" ", 1)[0] + "..."

    ramo_lower = ramo.lower()
    if "concurso" in ramo_lower:
        publico = "Candidatos aprovados fora das vagas, eliminados em fases subjetivas (psicotécnico, investigação social) ou com direito à nomeação por preterição."
    elif "militar" in ramo_lower:
        publico = "Militares das Forças Armadas ou Forças Auxiliares (ativos, da reserva, pensionistas ou ex-militares temporários) com demandas sobre soldo, pensão ou reforma."
    elif "servidor" in ramo_lower or "administrativo" in ramo_lower:
        publico = "Servidores públicos civis (federais ou estaduais), aposentados e pensionistas que possuem parcelas remuneratórias não reconhecidas ou gratificações suprimidas."
    else:
        publico = "Pessoas físicas ou jurídicas afetadas por atos administrativos correlatos com fundamentos idênticos ao precedente."

    analise_local = (
        f"📌 Explicação da Decisão:\n{resumo}\n\n"
        f"🎯 Público-Alvo e Oportunidades:\n{publico}\n\n"
        f"🏷️ Temas: {tags_str}"
    )
    return f"⚠️ {aviso_ia}\n\n{analise_local}" if aviso_ia else analise_local
