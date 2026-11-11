"""Interface de importação de PDFs, texto e endereços oficiais."""

from urllib.parse import urlparse

import requests
import streamlit as st

from database import (
    adicionar_a_fila_revisao,
    inserir_decisao,
    listar_fontes_oficiais,
    listar_fontes_recentes,
    registrar_fonte_verificada,
    sugerir_atualizacao_fonte,
)
from extractor import detectar_tribunal, extrair_decisoes_de_texto, extrair_texto_pdf
from agents.classifier.classifier import classificador_global
from services.audit import registrar_evento


def render_importacao(tab_importar, pode_editar: bool) -> None:
    """Renderiza os controles de importação no contexto da aba recebida."""
    if pode_editar and tab_importar is not None:
        with tab_importar:
            st.subheader("📥 Importação Inteligente de Boletim")
            st.caption("Extração automatizada de textos e PDFs integrada ao classificador temático de jurisprudência.")

            formato_importacao = st.radio(
                "Escolha a forma de importação:",
                ["🌐 Usar fonte oficial", "📄 Enviar PDF", "📋 Colar texto"],
                horizontal=True,
            )

            texto_para_processar = ""
            tribunal_sugerido = "TRF1"

            url_oficial = ""
            if formato_importacao != "🌐 Usar fonte oficial":
                st.session_state.pop("url_fonte_oficial", None)
                st.session_state.pop("texto_fonte_oficial", None)
            if formato_importacao == "🌐 Usar fonte oficial":
                st.caption("Escolha o tribunal e abra a página oficial para localizar o boletim. Cole aqui o link direto do PDF.")
                fontes_oficiais = listar_fontes_oficiais()
                tribunal_fonte = st.selectbox("Tribunal da fonte", ["TRF1", "TRF5", "TNU"])
                pagina_oficial = fontes_oficiais.get(tribunal_fonte, "")
                if pagina_oficial:
                    st.link_button(f"Abrir boletins oficiais do {tribunal_fonte}", pagina_oficial)
                if tribunal_fonte == "TNU":
                    st.caption("A página oficial pode listar boletins; para importar, use o link direto do PDF do boletim.")
                fontes_recentes = listar_fontes_recentes()
                recentes_do_tribunal = [f for f in fontes_recentes if f["tribunal"] == tribunal_fonte]
                urls_recentes = [f["url"] for f in recentes_do_tribunal]
                escolha_fonte = st.selectbox("PDFs deste tribunal que já deram resultado", ["Colar outro link"] + urls_recentes)
                if escolha_fonte == "Colar outro link":
                    url_oficial = st.text_input("Link direto do PDF oficial:", placeholder="https://...", key=f"pdf_url_{tribunal_fonte}")
                else:
                    url_oficial = escolha_fonte
                    detalhe_fonte = next(f for f in recentes_do_tribunal if f["url"] == escolha_fonte)
                    st.caption(f"Última extração encontrou {detalhe_fonte['candidatos_extraidos']} decisões · {detalhe_fonte['tribunal']}")
                    st.link_button("Abrir este PDF no navegador", escolha_fonte)

                with st.expander("Sugerir atualização da página oficial"):
                    st.caption("A sugestão será revisada pelo administrador antes de substituir o endereço predefinido.")
                    with st.form("sugerir_atualizacao_fonte"):
                        sugestao_url = st.text_input("Novo endereço oficial", placeholder="https://...")
                        enviar_sugestao = st.form_submit_button("Enviar sugestão")
                    if enviar_sugestao:
                        parsed_sugestao = urlparse(sugestao_url.strip())
                        host_sugestao = (parsed_sugestao.hostname or "").lower()
                        dominio_fonte = {"TRF1": "trf1.jus.br", "TRF5": "trf5.jus.br", "TNU": "cjf.jus.br"}[tribunal_fonte]
                        if parsed_sugestao.scheme != "https" or not (host_sugestao == dominio_fonte or host_sugestao.endswith("." + dominio_fonte)):
                            st.error(f"Informe um endereço HTTPS pertencente ao domínio oficial {dominio_fonte}.")
                        else:
                            sugerir_atualizacao_fonte(tribunal_fonte, sugestao_url, st.session_state.get("email_logado"))
                            registrar_evento(st.session_state.get("email_logado"), "sugerir_fonte", "tribunal", detalhes={"tribunal": tribunal_fonte})
                            st.success("Sugestão enviada para análise do administrador.")
                if st.button("🔎 Consultar endereço oficial"):
                    try:
                        if not url_oficial.strip():
                            raise ValueError("Informe ou selecione um endereço antes de consultar.")
                        st.session_state.pop("url_fonte_oficial", None)
                        st.session_state.pop("texto_fonte_oficial", None)
                        parsed = urlparse(url_oficial.strip())
                        host = (parsed.hostname or "").lower()
                        dominios_oficiais = ("trf1.jus.br", "trf5.jus.br", "cjf.jus.br")
                        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443) or not any(host == d or host.endswith("." + d) for d in dominios_oficiais):
                            st.error("Use um endereço HTTPS de TRF1, TRF5 ou CJF/TNU.")
                        else:
                            resposta = requests.get(url_oficial.strip(), timeout=20, headers={"User-Agent": "BoletimJurisprudencia/1.0"})
                            resposta.raise_for_status()
                            url_final = urlparse(resposta.url)
                            host_final = (url_final.hostname or "").lower()
                            if not any(host_final == d or host_final.endswith("." + d) for d in dominios_oficiais):
                                raise ValueError("O endereço redirecionou para fora dos domínios oficiais permitidos.")
                            if len(resposta.content) > 20 * 1024 * 1024:
                                raise ValueError("O arquivo excede o limite de 20 MB.")
                            if "pdf" not in resposta.headers.get("Content-Type", "").lower() and resposta.content[:4] != b"%PDF":
                                st.warning("Este endereço abriu uma página, não um boletim em PDF. Tente outro link, cole o endereço direto do PDF ou envie o arquivo.")
                                resposta = None
                            if resposta is None:
                                texto_buscado = ""
                            else:
                                texto_buscado = extrair_texto_pdf(resposta.content)
                            if not texto_buscado.strip():
                                st.warning("Não foi possível extrair texto deste PDF. Tente outro PDF ou cole o texto do boletim.")
                            elif resposta is not None:
                                st.session_state["texto_fonte_oficial"] = texto_buscado
                                st.session_state["url_fonte_oficial"] = resposta.url
                                st.success(f"PDF recebido ({len(texto_buscado)} caracteres). Confira os candidatos antes de enviá-los à revisão.")
                    except ValueError as exc:
                        st.warning(str(exc))
                    except Exception:
                        st.warning("Falha ao acessar ou ler este endereço. Confira se o link é direto para um PDF oficial ou envie o arquivo.")
                texto_para_processar = st.session_state.get("texto_fonte_oficial", "")
                if texto_para_processar:
                    tribunal_sugerido = detectar_tribunal(texto_para_processar)
            elif formato_importacao == "📄 Enviar PDF":
                arquivo_pdf = st.file_uploader("Selecione o arquivo PDF do Boletim:", type=["pdf"])
                if arquivo_pdf is not None:
                    bytes_pdf = arquivo_pdf.read()
                    with st.spinner("Lendo arquivo PDF e analisando texto..."):
                        texto_para_processar = extrair_texto_pdf(bytes_pdf)
                        tribunal_sugerido = detectar_tribunal(texto_para_processar)
                    st.success(f"PDF processado com sucesso! ({len(texto_para_processar)} caracteres). Tribunal sugerido: **{tribunal_sugerido}**.")
            else:
                texto_para_processar = st.text_area(
                    "Cole aqui o conteúdo do boletim informativo ou clipping:",
                    height=200,
                    placeholder="Cole o texto do boletim oficial aqui...",
                )
                if texto_para_processar:
                    tribunal_sugerido = detectar_tribunal(texto_para_processar)

            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                tribunal_escolhido = st.selectbox(
                    "Confirmar Tribunal do Boletim:",
                    ["TRF1", "TRF5", "TNU", "STF", "STJ", "TRU5", "Outros"],
                    index=["TRF1", "TRF5", "TNU", "STF", "STJ", "TRU5", "Outros"].index(tribunal_sugerido)
                    if tribunal_sugerido in ["TRF1", "TRF5", "TNU", "STF", "STJ", "TRU5", "Outros"]
                    else 0,
                )
            with col_cfg2:
                if formato_importacao == "📋 Colar texto":
                    apenas_adm_militar = False
                    st.caption("Texto colado: serão mantidos todos os blocos, sem filtro temático.")
                else:
                    apenas_adm_militar = st.checkbox(
                        "🎯 Filtrar apenas decisões de Direito Administrativo e Militar",
                        value=True,
                        key=f"filtro_tema_{formato_importacao}",
                    )

            if st.button("⚡ Ler Boletim e Extrair Decisões", type="primary", use_container_width=True):
                if not texto_para_processar.strip():
                    st.warning("Não há texto extraível neste endereço. Use o link direto do PDF, envie o arquivo ou cole o texto.")
                else:
                    with st.spinner("Analisando estrutura, identificando teses, prazos e classificando matérias..."):
                        candidatos = extrair_decisoes_de_texto(
                            texto_para_processar,
                            tribunal_padrao=tribunal_escolhido,
                            apenas_adm_militar=apenas_adm_militar,
                        )
                        st.session_state["decisoes_extraidas_temp"] = candidatos
                        st.session_state["origem_extracao_temp"] = st.session_state.get("url_fonte_oficial", "") if formato_importacao == "🌐 Usar fonte oficial" else "PDF ou texto fornecido pelo usuário"
                        if formato_importacao == "🌐 Usar fonte oficial" and candidatos:
                            registrar_fonte_verificada(
                                st.session_state.get("url_fonte_oficial", ""), tribunal_escolhido, len(candidatos)
                            )

            if "decisoes_extraidas_temp" in st.session_state and st.session_state["decisoes_extraidas_temp"]:
                candidatos = st.session_state["decisoes_extraidas_temp"]
                st.markdown(f"### 📋 Decisões Identificadas ({len(candidatos)})")
                st.caption("A fila recebe os candidatos agora; a confirmação na aba Revisão fará a inclusão na base oficial.")
                st.info("Confira a quantidade e a prévia. Se o texto tiver mais decisões, prefira separar cada bloco com ‘Decisão 01’, ‘Decisão 02’ e assim por diante.")
                faltam_decisoes = st.radio(
                    "Depois de conferir a prévia, ficou alguma decisão de fora?",
                    ["Não, encontrei todas", "Sim ou não tenho certeza"],
                    horizontal=True,
                )
                if faltam_decisoes == "Sim ou não tenho certeza":
                    st.warning("Envie o trecho ou as páginas restantes como complemento. Para texto colado, separe os blocos com marcadores como ‘Decisão 01’ e ‘Decisão 02’.")
                col_acoes1, col_acoes2 = st.columns(2)
                with col_acoes1:
                    if st.button("📥 Migrar todas para revisão", type="primary", use_container_width=True):
                        for cand in candidatos:
                            if st.session_state.get("url_fonte_oficial"):
                                cand["link_oficial"] = st.session_state["url_fonte_oficial"]
                            adicionar_a_fila_revisao(
                                cand,
                                origem=st.session_state.get("origem_extracao_temp"),
                                documento=st.session_state.get("url_fonte_oficial") or "PDF/texto importado",
                                criado_por=st.session_state.get("email_logado"),
                            )
                        registrar_evento(st.session_state.get("email_logado"), "enfileirar_candidatos", "fila_revisao", detalhes={"quantidade": len(candidatos)})
                        del st.session_state["decisoes_extraidas_temp"]
                        st.success(f"{len(candidatos)} decisões enviadas à fila de revisão.")
                        st.rerun()

                with col_acoes2:
                    if st.button("💾 Salvar direto na base oficial", use_container_width=True):
                        salvos = 0
                        duplicados = 0
                        origem_nome = st.session_state.get("origem_extracao_temp", "Importação")
                        for cand in candidatos:
                            if st.session_state.get("url_fonte_oficial"):
                                cand["link_oficial"] = st.session_state["url_fonte_oficial"]
                            nid = inserir_decisao(
                                cand,
                                usuario=st.session_state.get("email_logado"),
                                origem=origem_nome,
                            )
                            if nid > 0:
                                salvos += 1
                            else:
                                duplicados += 1
                        msg = f"{salvos} decisões salvas na base oficial!"
                        if duplicados > 0:
                            msg += f" ({duplicados} ignoradas por duplicidade)"
                        st.success(msg)
                        del st.session_state["decisoes_extraidas_temp"]
                        st.rerun()

                with st.expander("Prévia dos candidatos encontrados", expanded=True):
                    for idx_c, cand in enumerate(candidatos):
                        st.markdown(f"**{cand['identificador']} — {cand['titulo']}**")
                        sugestao_relevancia = classificador_global.sugerir_relevancia(cand)
                        st.info(f"💡 **Sugestão de Relevância temática:** {sugestao_relevancia}")
                        st.caption(
                            f"Tribunal: {cand['tribunal']} · Tipo: {cand['tipo']} · Ramo: {cand['ramo']}\n\n"
                            f"Processo: {cand['processo_origem'] or 'não identificado'} · Data: {cand['data_evento'] or 'não identificada'} · "
                            f"Relator: {cand['relator'] or 'não identificado'} · Órgão: {cand['orgao_julgador'] or 'não identificado'} · "
                            f"Situação: {cand['status']}"
                        )
                        st.write(cand.get("texto_original") or cand["tese_resumo"])

                        with st.expander(f"✏️ Editar dados de {cand['identificador']}", expanded=False):
                            with st.form(f"form_editar_cand_{idx_c}"):
                                opcoes_trib = ["TRF1", "TRF5", "TNU", "TRU5", "STJ", "STF", "Outros"]
                                idx_t = opcoes_trib.index(cand["tribunal"]) if cand["tribunal"] in opcoes_trib else 0
                                e_tribunal = st.selectbox("Tribunal", opcoes_trib, index=idx_t)
                                e_ident = st.text_input("Identificador", value=cand.get("identificador", ""))
                                e_titulo = st.text_input("Título", value=cand.get("titulo", ""))
                                e_ramo = st.text_input("Ramo", value=cand.get("ramo", ""))
                                e_proc = st.text_input("Processo", value=cand.get("processo_origem", ""))
                                e_resumo = st.text_area("Tese / Resumo", value=cand.get("tese_resumo", ""))
                                submit_edit = st.form_submit_button("Salvar alterações deste candidato")
                                if submit_edit:
                                    cand["tribunal"] = e_tribunal
                                    cand["identificador"] = e_ident
                                    cand["titulo"] = e_titulo
                                    cand["ramo"] = e_ramo
                                    cand["processo_origem"] = e_proc
                                    cand["tese_resumo"] = e_resumo
                                    st.session_state["decisoes_extraidas_temp"][idx_c] = cand
                                    st.success("Candidato atualizado com sucesso!")
                                    st.rerun()

                        st.divider()
                if st.button("Descartar esta extração"):
                    del st.session_state["decisoes_extraidas_temp"]
                    st.rerun()
            elif "decisoes_extraidas_temp" in st.session_state:
                st.warning("Não foi possível identificar decisões neste conteúdo. Tente o PDF direto ou cole o texto com os blocos separados.")


