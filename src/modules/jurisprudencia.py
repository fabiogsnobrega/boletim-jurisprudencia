"""Radar de acompanhamento de prazos de jurisprudência."""

from datetime import date, datetime, timedelta
import io

import pandas as pd

import streamlit as st

from database import (
    atualizar_verificacao,
    excluir_decisao,
    excluir_decisoes,
    encontrar_grupos_duplicados,
    listar_decisoes,
)
from modules.prazos import calcular_prazo
from services.audit import registrar_evento

def render_radar(tab_alertas, filtro_tribunal, filtro_ramo, busca_texto, pode_editar: bool) -> None:
    """Renderiza o fluxo correspondente dentro da aba informada."""
    # -------------------------------------------------------------
    # ABA 2: RADAR DE ALERTAS (MONITORAMENTO DE PRAZOS)
    # -------------------------------------------------------------
    with tab_alertas:
        st.subheader("🚨 Painel de Acompanhamento e Prazos")

        # Consulta os alertas ordenados por urgência (prazos mais próximos de vencer primeiro)
        alertas_lista = listar_decisoes(
            tribunal=filtro_tribunal,
            ramo=filtro_ramo,
            somente_alertas=True,
            busca=busca_texto if busca_texto else None,
            ordem="alerta_prazo",
        )

        if not alertas_lista:
            st.success("Não há nenhum alerta pendente para os filtros selecionados!")
        else:
            for item in alertas_lista:
                data_limite_str = item.get("data_limite_verificacao") or date.today().strftime("%Y-%m-%d")
                dias_restantes, texto_prazo, classe_badge = calcular_prazo(data_limite_str)

                borda_card = "3px solid #DC2626" if dias_restantes <= 0 else "3px solid #D89C1B"
                num_reg_fmt = f"{item['id']:02d}"

                alerta_card_html = (
                    f'<div class="alerta-card" style="border: 1px solid #E6E4DF; border-left: {borda_card};">'
                    f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">'
                    f'<div>'
                    f'<span class="badge-registro">Nº {num_reg_fmt}</span>'
                    f'<span class="badge-tribunal">{item["tribunal"]}</span>'
                    f'<span class="badge-ramo">{item["ramo"]}</span>'
                    f'<span class="badge-status">Status: {item["status"]}</span>'
                    f'</div>'
                    f'<span class="{classe_badge}">{texto_prazo}</span>'
                    f'</div>'
                    f'<h3 class="noticia-title" style="margin-top: 12px !important;">{item["identificador"]} - {item["titulo"]}</h3>'
                    f'<p style="color: #5C6B7E; margin-bottom: 8px; font-size: 0.9rem;">'
                    f'<strong>Processo:</strong> {item["processo_origem"] or "N/A"} | '
                    f'<strong>Órgão:</strong> {item["orgao_julgador"] or "N/A"} | '
                    f'<strong>Data do Evento:</strong> {item["data_evento"] or "N/A"}'
                    f'</p>'
                    f'<div class="tese-box" style="margin-top: 10px;">'
                    f'<strong>Questão em debate / Tese:</strong><br>{item["tese_resumo"]}'
                    f'</div>'
                    f'<div class="comentario-box">'
                    f'<strong>Orientação para acompanhamento:</strong><br>{item["conclusao_comentarios"] or "Acompanhar publicação de novo acórdão ou inclusão em pauta."}'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(alerta_card_html, unsafe_allow_html=True)

                # Controles de ação para usuários autorizados
                if pode_editar:
                    col_act1, col_act2, col_act3, col_act4 = st.columns([1, 1, 1.2, 0.8])
                    with col_act1:
                        if st.button("➕ Adiar 15 dias", key=f"adiar15_{item['id']}"):
                            nova_data = (date.today() + timedelta(days=15)).strftime("%Y-%m-%d")
                            atualizar_verificacao(item["id"], nova_data_limite=nova_data)
                            registrar_evento(st.session_state.get("email_logado"), "adiar_prazo", "decisao", item["id"], {"dias": 15})
                            st.toast(f"Registro Nº {num_reg_fmt} prorrogado em 15 dias!")
                            st.rerun()
                    with col_act2:
                        if st.button("➕ Adiar 30 dias", key=f"adiar30_{item['id']}"):
                            nova_data = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
                            atualizar_verificacao(item["id"], nova_data_limite=nova_data)
                            registrar_evento(st.session_state.get("email_logado"), "adiar_prazo", "decisao", item["id"], {"dias": 30})
                            st.toast(f"Registro Nº {num_reg_fmt} prorrogado em 30 dias!")
                            st.rerun()
                    with col_act3:
                        if st.button("✅ Concluir / Transitou", key=f"transitou_{item['id']}"):
                            atualizar_verificacao(item["id"], remover_alerta=True, novo_status="Transitado em Julgado")
                            registrar_evento(st.session_state.get("email_logado"), "concluir_acompanhamento", "decisao", item["id"])
                            st.toast(f"Registro Nº {num_reg_fmt} concluído e marcado como Transitado!")
                            st.rerun()
                    with col_act4:
                        if st.button("🗑️ Excluir", key=f"del_alerta_{item['id']}"):
                            excluir_decisao(item["id"])
                            registrar_evento(st.session_state.get("email_logado"), "excluir", "decisao", item["id"])
                            st.toast(f"Registro Nº {num_reg_fmt} excluído!")
                            st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)






def render_base_tabular(tab_tabela, todas_decisoes, pode_editar: bool) -> None:
    """Renderiza a base pesquisável e as opções de exportação e manutenção."""
    with tab_tabela:
        st.subheader("📊 Base de Dados Estruturada")

        if todas_decisoes:
            df = pd.DataFrame(todas_decisoes)

            # Número do registro
            df["Nº do Registro"] = df["id"].apply(lambda x: f"{x:02d}")

            # Formatação dos valores
            df["ramo"] = df["ramo"].fillna("").str.title()
            df["status"] = df["status"].fillna("").str.title()
            df["em_alerta"] = df["em_alerta"].map({1: "Sim", 0: "Não"}).fillna("")
            df = df.fillna("")

            colunas_exibicao = [
                "Nº do Registro",
                "tribunal",
                "identificador",
                "titulo",
                "ramo",
                "status",
                "em_alerta",
                "data_limite_verificacao",
                "data_evento",
                "processo_origem",
            ]

            nomes_exibicao = {
                "Nº do Registro": "Nº do Registro",
                "tribunal": "Tribunal",
                "identificador": "Identificador",
                "titulo": "Título",
                "ramo": "Ramo",
                "status": "Status",
                "em_alerta": "Em Alerta",
                "data_limite_verificacao": "Data Limite Verificação",
                "data_evento": "Data do Evento",
                "processo_origem": "Processo Origem",
            }

            st.dataframe(
                df[colunas_exibicao].rename(columns=nomes_exibicao),
                width="stretch",
                hide_index=True,
            )

            if pode_editar:
                with st.expander("🗑️ Excluir Registro por Número"):
                    col_id, col_btn_del = st.columns([2, 1])
                    id_para_excluir = col_id.selectbox(
                        "Selecione o registro para excluir:",
                        options=[d["id"] for d in todas_decisoes],
                        format_func=lambda x: f"Nº {x:02d} - {[d['identificador'] for d in todas_decisoes if d['id'] == x][0]} - {[d['titulo'] for d in todas_decisoes if d['id'] == x][0]}",
                    )
                    if col_btn_del.button("Confirmar Exclusão", type="secondary"):
                        excluir_decisao(id_para_excluir)
                        st.toast(f"Registro Nº {id_para_excluir:02d} excluído!")
                        st.rerun()

            col_exp1, col_exp2 = st.columns(2)

            # Exportar CSV
            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            col_exp1.download_button(
                label="📥 Exportar Base Completa em CSV",
                data=csv_data,
                file_name=f"boletim_jurisprudencia_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                width="stretch",
            )

            # Exportar Excel
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Jurisprudencia")
            excel_data = excel_buffer.getvalue()

            col_exp2.download_button(
                label="📊 Exportar Base Completa em Excel (.xlsx)",
                data=excel_data,
                file_name=f"boletim_jurisprudencia_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        else:
            st.info("A base está vazia.")

        if pode_editar:
            with st.expander("🔎 Localizar possíveis duplicatas"):
                grupos_duplicados = encontrar_grupos_duplicados()
                copias_excedentes = sum(len(grupo) - 1 for grupo in grupos_duplicados)
                if not grupos_duplicados:
                    st.success("Não encontrei processos CNJ repetidos nesta base.")
                else:
                    st.warning(f"Encontrei {len(grupos_duplicados)} grupo(s), com {copias_excedentes} cópia(s) excedente(s). A versão com mais conteúdo será mantida.")
                    for grupo in grupos_duplicados:
                        principal = grupo[0]
                        resumo_ids = ", ".join(
                            "{} ({} caracteres)".format(reg["id"], reg["_tamanho_conteudo"])
                            for reg in grupo
                        )
                        st.markdown(
                            f"**{principal['tribunal']} · {principal['processo_origem'] or principal['identificador']}**  "
                            f"IDs: {resumo_ids}"
                        )
                    confirmar_duplicatas = st.checkbox("Confirmo a exclusão das cópias listadas", key="confirmar_excluir_duplicatas")
                    if st.button("Excluir cópias e manter a versão mais completa", key="excluir_duplicatas"):
                        if confirmar_duplicatas:
                            ids_duplicados = [registro["id"] for grupo in grupos_duplicados for registro in grupo[1:]]
                            apagadas = excluir_decisoes(ids_duplicados)
                            registrar_evento(st.session_state.get("email_logado"), "deduplicar", "decisoes", detalhes={"removidas": apagadas})
                            st.success(f"{apagadas} cópias removidas.")
                            st.rerun()
                        else:
                            st.error("Marque a confirmação antes de excluir as cópias.")


