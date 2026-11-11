"""Renderização da fila de revisão e composição de observações sugeridas."""

import math
import re

import streamlit as st

from database import (
    aceitar_candidato,
    aceitar_candidatos_em_lote,
    atualizar_candidato,
    encontrar_duplicatas_fila,
    excluir_candidatos_fila,
    excluir_todas_pendencias_revisao,
    listar_fila_revisao,
    rejeitar_candidatos_em_lote,
    revisar_candidato,
)
from agents.classifier.classifier import classificador_global
from services.audit import registrar_evento


def gerar_sugestao_observacao(dados: dict) -> str:
    """Cria um rascunho curto a partir do conteúdo extraído, sem chamada a modelo."""
    conteudo = " ".join(str(dados.get("texto_original") or dados.get("tese_resumo") or "").split())
    conteudo = re.sub(r"^Boletim Informativo de Jurisprudência\s*[•·-]?\s*\d*\s*", "", conteudo, flags=re.IGNORECASE)
    frases = re.split(r"(?<=[.!?])\s+", conteudo)
    resumo = " ".join(frases[:2]).strip()
    if len(resumo) > 360:
        resumo = resumo[:357].rsplit(" ", 1)[0] + "..."
    if not resumo:
        resumo = str(dados.get("titulo") or "Conteúdo da decisão ainda precisa ser conferido.")

    ramo = str(dados.get("ramo") or "").casefold()
    if "concurso" in ramo:
        utilizacao = "Pode servir de referência em demandas de concurso público com discussão semelhante sobre edital, convocação, nomeação ou preterição."
    elif "militar" in ramo:
        utilizacao = "Pode servir de referência em demandas de militares com fatos e fundamento jurídico semelhantes."
    elif "servidor" in ramo or "administrativo" in ramo:
        utilizacao = "Pode servir de referência em demandas de servidores ou de Direito Administrativo com fatos e fundamento jurídico semelhantes."
    else:
        utilizacao = "Pode servir de referência em casos com fatos e fundamento jurídico semelhantes, após conferência da aderência ao caso concreto."
    return f"Resumo da demanda: {resumo}\n\nPossível utilização: {utilizacao}"


def render_review_tab(tab_revisao, pode_editar: bool) -> None:
    """Renderiza o fluxo de revisão em lote e individual da fila."""
    if pode_editar and tab_revisao is not None:
        with tab_revisao:
            pendentes = listar_fila_revisao()
            st.subheader("📋 Decisões aguardando revisão")
            st.caption("Selecione decisões para adicionar ou excluir em lote, ou abra para conferir detalhes e editar.")

            grupos_fila_duplicados = encontrar_duplicatas_fila()
            if grupos_fila_duplicados:
                total_copias_fila = sum(len(grupo) - 1 for grupo in grupos_fila_duplicados)
                with st.expander(f"Possíveis duplicatas na fila ({total_copias_fila} cópias)"):
                    st.caption("Agrupadas pelo mesmo tribunal e número de processo CNJ. Em cada grupo, a versão com mais conteúdo será mantida.")
                    for grupo in grupos_fila_duplicados:
                        st.markdown(
                            f"**{grupo[0]['dados'].get('tribunal')} · {grupo[0]['dados'].get('processo_origem') or grupo[0]['dados'].get('identificador')}**"
                        )
                        for registro in grupo:
                            st.caption(
                                f"ID {registro['id']} · {registro['dados'].get('titulo', '')} · "
                                f"{registro['dados']['_tamanho_conteudo']} caracteres"
                            )
                    confirmar_deduplicacao_fila = st.checkbox("Confirmo a remoção das cópias identificadas", key="confirmar_deduplicacao_fila")
                    if st.button("Remover cópias da fila", key="remover_duplicatas_fila"):
                        if confirmar_deduplicacao_fila:
                            ids_remover = [registro["id"] for grupo in grupos_fila_duplicados for registro in grupo[1:]]
                            removidas = excluir_candidatos_fila(ids_remover)
                            registrar_evento(st.session_state.get("email_logado"), "deduplicar", "fila_revisao", detalhes={"removidas": removidas})
                            st.success(f"{removidas} cópias removidas da fila.")
                            st.rerun()
                        else:
                            st.error("Marque a confirmação para remover as cópias.")

            with st.expander("Limpar fila de revisão"):
                st.warning(f"Esta ação exclui as {len(pendentes)} pendências atuais. Itens já aceitos ou rejeitados serão preservados.")
                confirmar_limpeza = st.checkbox("Confirmo a exclusão de todas as pendências", key="confirmar_limpeza_fila")
                if st.button("Excluir todas as pendências", key="limpar_fila_revisao"):
                    if confirmar_limpeza:
                        removidas = excluir_todas_pendencias_revisao()
                        registrar_evento(st.session_state.get("email_logado"), "excluir_pendencias", "fila_revisao", detalhes={"removidas": removidas})
                        st.success(f"{removidas} pendências excluídas.")
                        st.rerun()
                    else:
                        st.error("Marque a confirmação para excluir a fila.")

            if not pendentes:
                st.success("Não há decisões pendentes de revisão.")
                return

            total_pendentes = len(pendentes)
            itens_por_pagina = 15
            total_paginas = max(1, math.ceil(total_pendentes / itens_por_pagina))

            if "pagina_revisao_atual" not in st.session_state:
                st.session_state["pagina_revisao_atual"] = 1
            st.session_state["pagina_revisao_atual"] = min(
                max(1, int(st.session_state["pagina_revisao_atual"])), total_paginas
            )
            pagina_atual = int(st.session_state["pagina_revisao_atual"])

            inicio_idx = (pagina_atual - 1) * itens_por_pagina
            fim_idx = min(inicio_idx + itens_por_pagina, total_pendentes)
            lote = pendentes[inicio_idx:fim_idx]

            # Contagem de selecionados globais e da página atual
            selecionados_pagina = [item["id"] for item in lote if st.session_state.get(f"sel_revisao_{item['id']}", False)]
            selecionados_todos = [item["id"] for item in pendentes if st.session_state.get(f"sel_revisao_{item['id']}", False)]

            # Barra superior de controle de lote e paginação
            st.markdown("---")
            col_bar1, col_bar2, col_bar3 = st.columns([2.5, 3, 2.5])
            with col_bar1:
                st.write(f"📊 **{total_pendentes} decisões pendentes**")
                col_sel_all, col_unsel = st.columns(2)
                if col_sel_all.button("☑️ Marcar todas (15)", key="marcar_todas_pag", use_container_width=True):
                    for item in lote:
                        st.session_state[f"sel_revisao_{item['id']}"] = True
                    st.rerun()
                if col_unsel.button("⬜ Desmarcar todas", key="desmarcar_todas_pag", use_container_width=True):
                    for item in pendentes:
                        st.session_state[f"sel_revisao_{item['id']}"] = False
                    st.rerun()

            with col_bar2:
                col_p_ant, col_p_info, col_p_prox = st.columns([1, 2, 1])
                with col_p_ant:
                    if st.button("⬅️ Anterior", disabled=(pagina_atual <= 1), use_container_width=True, key="pag_ant_top"):
                        st.session_state["pagina_revisao_atual"] = pagina_atual - 1
                        st.rerun()
                with col_p_info:
                    st.markdown(
                        f"<div style='text-align: center; padding-top: 6px; font-size: 0.92rem; font-weight: 600;'>"
                        f"Página {pagina_atual} de {total_paginas}<br>"
                        f"<span style='font-size: 0.8rem; font-weight: normal; color: #555;'>Itens {inicio_idx + 1} a {fim_idx}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_p_prox:
                    if st.button("Próxima ➡️", disabled=(pagina_atual >= total_paginas), use_container_width=True, key="pag_prox_top"):
                        st.session_state["pagina_revisao_atual"] = pagina_atual + 1
                        st.rerun()

            with col_bar3:
                st.write(f"📌 **{len(selecionados_todos)} selecionada(s)**")
                if len(selecionados_todos) > 0:
                    st.caption("Ações rápidas disponíveis no final da página.")

            st.markdown("---")

            # Lista das 15 decisões com caixa de seleção na frente do número
            for idx_relativo, item in enumerate(lote, start=1):
                num_global = inicio_idx + idx_relativo
                dados = item["dados"]
                item_id = item["id"]

                col_chk, col_card = st.columns([0.07, 0.93])
                with col_chk:
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    st.checkbox(
                        "",
                        key=f"sel_revisao_{item_id}",
                        help=f"Marcar #{num_global} para ação em lote",
                    )

                with col_card:
                    titulo_expander = f"#{num_global} · {dados.get('identificador', 'Sem identificador')} — {dados.get('titulo', 'Sem título')}"
                    with st.expander(titulo_expander, expanded=False):
                        st.caption(
                            f"Origem: {item.get('origem') or 'não informada'} · "
                            f"Documento: {item.get('documento') or 'não informado'} · "
                            f"Enviado por: {item.get('criado_por') or 'não identificado'}"
                        )
                        if dados.get("avisos_validacao"):
                            st.warning("Conferir estes pontos: " + " · ".join(dados["avisos_validacao"]))

                        st.markdown(
                            f"**Tribunal:** {dados.get('tribunal', 'não identificado')} · **Tipo:** {dados.get('tipo') or 'não identificado'} · "
                            f"**Ramo:** {dados.get('ramo') or 'não identificado'}\n\n"
                            f"**Processo:** {dados.get('processo_origem') or 'não identificado'} · **Data:** {dados.get('data_evento') or 'não identificada'}\n\n"
                            f"**Situação:** {dados.get('status') or 'não identificada'} · **Relator:** {dados.get('relator') or 'não identificado'} · "
                            f"**Órgão julgador:** {dados.get('orgao_julgador') or 'não identificado'}"
                        )
                        if dados.get("em_alerta"):
                            st.warning(f"Acompanhamento sugerido: {dados.get('prazo_alerta') or 'prazo a revisar'}")

                        st.markdown("**Tese / conteúdo extraído:**")
                        st.write(dados.get("texto_original") or dados.get("tese_resumo") or "O documento não forneceu texto para este campo.")

                        sugestao_relevancia = classificador_global.sugerir_relevancia(dados)
                        st.info(f"🎯 **Classificador Temático:** {sugestao_relevancia}")

                        sugestao_observacao = gerar_sugestao_observacao(dados)
                        st.info(f"💡 Sugestão de observação — rascunho para conferência\n\n{sugestao_observacao}")
                        usar_sugestao = st.checkbox("Aceitar a sugestão como observação", key=f"usar_sugestao_{item_id}")
                        observacao_extra = st.text_area("Observação pessoal ou complemento (opcional)", key=f"obs_extra_{item_id}")
                        comentario_final = "\n\n".join(
                            parte for parte in (sugestao_observacao if usar_sugestao else "", observacao_extra.strip()) if parte
                        ) or None
                        st.caption(f"Fonte: {dados.get('link_oficial') or item.get('documento') or 'não informada'}")

                        editar_campos = st.checkbox("Editar os dados extraídos", key=f"editar_{item_id}")
                        if editar_campos:
                            opcoes_tribunal = ["TRF1", "TRF5", "TNU", "TRU5", "STJ", "STF", "Outros"]
                            idx_tribunal = opcoes_tribunal.index(dados.get("tribunal", "Outros")) if dados.get("tribunal") in opcoes_tribunal else 6
                            dados_revisados = dict(dados)
                            dados_revisados["tribunal"] = st.selectbox("Tribunal", opcoes_tribunal, index=idx_tribunal, key=f"trib_{item_id}")
                            dados_revisados["identificador"] = st.text_input("Identificador", value=dados.get("identificador", ""), key=f"ident_{item_id}")
                            dados_revisados["titulo"] = st.text_input("Título", value=dados.get("titulo", ""), key=f"titulo_{item_id}")
                            dados_revisados["processo_origem"] = st.text_input("Processo de origem", value=dados.get("processo_origem", ""), key=f"proc_{item_id}")
                            dados_revisados["data_evento"] = st.text_input("Data do evento", value=dados.get("data_evento", ""), key=f"data_{item_id}")
                            dados_revisados["ramo"] = st.text_input("Ramo do Direito", value=dados.get("ramo", ""), key=f"ramo_{item_id}")
                            dados_revisados["tese_resumo"] = st.text_area("Tese / síntese", value=dados.get("tese_resumo", ""), key=f"tese_{item_id}")
                        else:
                            dados_revisados = dados

                        c_ok, c_no = st.columns(2)
                        if c_ok.button("✅ Aceitar individualmente", type="primary", key=f"aceitar_{item_id}", use_container_width=True):
                            if not str(dados_revisados.get("identificador") or "").strip() or not str(dados_revisados.get("titulo") or "").strip() or not str(dados_revisados.get("tese_resumo") or "").strip():
                                st.error("Identificador, título e conteúdo são necessários para incluir a decisão.")
                            else:
                                atualizar_candidato(item_id, dados_revisados)
                                if aceitar_candidato(item_id, comentario_final, st.session_state.get("email_logado")):
                                    st.session_state.pop(f"sel_revisao_{item_id}", None)
                                    registrar_evento(st.session_state.get("email_logado"), "aceitar", "candidato", item_id)
                                    st.toast("Decisão incluída na base.")
                                    st.rerun()

                        if c_no.button("⛔ Rejeitar individualmente", key=f"rejeitar_{item_id}", use_container_width=True):
                            if revisar_candidato(item_id, "rejeitada", comentario_final, st.session_state.get("email_logado")):
                                st.session_state.pop(f"sel_revisao_{item_id}", None)
                                registrar_evento(st.session_state.get("email_logado"), "rejeitar", "candidato", item_id)
                                st.toast("Candidato rejeitado.")
                                st.rerun()

            # Paginação no rodapé
            st.markdown("---")
            col_bot_ant, col_bot_info, col_bot_prox = st.columns([1, 2, 1])
            with col_bot_ant:
                if st.button("⬅️ Página Anterior", disabled=(pagina_atual <= 1), use_container_width=True, key="pag_ant_bot"):
                    st.session_state["pagina_revisao_atual"] = pagina_atual - 1
                    st.rerun()
            with col_bot_info:
                st.markdown(
                    f"<div style='text-align: center; padding-top: 6px; font-weight: 600;'>"
                    f"Página {pagina_atual} de {total_paginas} ({inicio_idx + 1} a {fim_idx} de {total_pendentes})"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_bot_prox:
                if st.button("Próxima Página ➡️", disabled=(pagina_atual >= total_paginas), use_container_width=True, key="pag_prox_bot"):
                    st.session_state["pagina_revisao_atual"] = pagina_atual + 1
                    st.rerun()

            # PAINEL DE AÇÕES EM LOTE AO FINAL DA PÁGINA
            total_selecionadas = len(selecionados_todos)
            st.markdown(f"### ⚡ Processar Decisões Selecionadas ({total_selecionadas})")
            if total_selecionadas == 0:
                st.info("💡 Marque a caixa de seleção na frente de cada decisão (ou clique em '☑️ Marcar todas') para adicionar ou rejeitar em lote rapidamente.")

            col_lote_add, col_lote_del, col_lote_clear = st.columns([2.5, 2.5, 1.5])
            with col_lote_add:
                label_add = f"✅ Adicionar {total_selecionadas} decisões" if total_selecionadas > 0 else "✅ Adicionar decisões selecionadas"
                if st.button(label_add, type="primary", disabled=(total_selecionadas == 0), use_container_width=True, key="btn_lote_adicionar"):
                    with st.spinner("Gravando decisões selecionadas na base oficial..."):
                        aceitos, dups = aceitar_candidatos_em_lote(
                            selecionados_todos, revisor=st.session_state.get("email_logado")
                        )
                        for sid in selecionados_todos:
                            st.session_state.pop(f"sel_revisao_{sid}", None)
                        msg_sucesso = f"🎉 {aceitos} decisão(ões) adicionada(s) à base oficial com sucesso!"
                        if dups > 0:
                            msg_sucesso += f" ({dups} duplicata(s) descartada(s))"
                        st.success(msg_sucesso)
                        st.rerun()

            with col_lote_del:
                label_del = f"⛔ Excluir / Rejeitar {total_selecionadas} decisões" if total_selecionadas > 0 else "⛔ Excluir / Rejeitar decisões selecionadas"
                if st.button(label_del, disabled=(total_selecionadas == 0), use_container_width=True, key="btn_lote_excluir"):
                    with st.spinner("Rejeitando decisões selecionadas..."):
                        rejeitados = rejeitar_candidatos_em_lote(
                            selecionados_todos, revisor=st.session_state.get("email_logado")
                        )
                        for sid in selecionados_todos:
                            st.session_state.pop(f"sel_revisao_{sid}", None)
                        st.warning(f"🗑️ {rejeitados} decisão(ões) rejeitada(s) e removida(s) da fila.")
                        st.rerun()

            with col_lote_clear:
                if st.button("Limpar seleção", disabled=(total_selecionadas == 0), use_container_width=True, key="btn_lote_limpar"):
                    for sid in selecionados_todos:
                        st.session_state[f"sel_revisao_{sid}"] = False
                    st.rerun()
