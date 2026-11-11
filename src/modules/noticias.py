"""Noticiário jurídico em cartões de leitura."""

import streamlit as st

from database import excluir_decisao
from modules.prazos import calcular_prazo
from services.audit import registrar_evento

def render_noticias(tab_noticias, decisoes_filtradas, pode_editar: bool) -> None:
    """Renderiza o fluxo correspondente dentro da aba informada."""
    # -------------------------------------------------------------
    # ABA 1: NOTICIÁRIO JURÍDICO (CARDS COM PALETA IDA LEGAL)
    # -------------------------------------------------------------
    with tab_noticias:
        st.subheader("📰 Notícias e Teses Consolidadas")

        if not decisoes_filtradas:
            st.info("Nenhuma decisão encontrada com os critérios de filtro selecionados.")
        else:
            for idx_seq, item in enumerate(decisoes_filtradas, start=1):
                alerta_tag = ""
                if item["em_alerta"]:
                    if item.get("data_limite_verificacao"):
                        _, texto_prazo, classe_badge = calcular_prazo(item["data_limite_verificacao"])
                        alerta_tag = f"<span class='{classe_badge}'>{texto_prazo}</span>"
                    else:
                        alerta_tag = f"<span class='badge-alerta-hoje'>🚨 ACOMPANHAR: {item['prazo_alerta']}</span>"

                num_reg_fmt = f"{item['id']:02d}"

                # Construção do card no padrão IDA Legal (sem quebras de linha com indentação para evitar bloco de código markdown)
                link_html = f"<div style='margin-top: 8px;'><a href='{item['link_oficial']}' target='_blank' style='color: #122449; font-weight: 600; text-decoration: none;'>🔗 Consultar decisão no portal oficial →</a></div>" if item["link_oficial"] else ""
                proc_html = f"<div style='color: #5C6B7E; font-size: 0.88rem; margin-top: 4px;'><strong>Processo Paradigma:</strong> <code>{item['processo_origem']}</code></div>" if item["processo_origem"] else ""
                coment_html = f"<div class='comentario-box'><strong>💡 Comentários / Conclusão Prática:</strong><br>{item['conclusao_comentarios']}</div>" if item["conclusao_comentarios"] else ""

                card_html = (
                    f'<div class="noticia-card">'
                    f'<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">'
                    f'<div>'
                    f'<span class="badge-registro">Nº {num_reg_fmt}</span>'
                    f'<span class="badge-tribunal">{item["tribunal"]}</span>'
                    f'<span class="badge-ramo">{item["ramo"]}</span>'
                    f'<span class="badge-status">{item["status"]}</span>'
                    f'</div>'
                    f'<div>{alerta_tag}</div>'
                    f'</div>'
                    f'<h3 class="noticia-title">{item["titulo"]}</h3>'
                    f'<div style="color: #5C6B7E; font-size: 0.9rem; margin-bottom: 8px;">'
                    f'<strong>{item["identificador"]}</strong> • {item["tipo"]} • '
                    f'Órgão: <em>{item["orgao_julgador"] or "N/A"}</em> • '
                    f'Relator: <em>{item["relator"] or "N/A"}</em> • '
                    f'Data: <em>{item["data_evento"] or "N/A"}</em>'
                    f'</div>'
                    f'{proc_html}'
                    f'<div class="tese-box"><strong>📌 Tese / Decisão:</strong><br>{item["tese_resumo"]}</div>'
                    f'{coment_html}'
                    f'{link_html}'
                    f'</div>'
                )

                if pode_editar:
                    c_card, c_del = st.columns([0.94, 0.06])
                    with c_card:
                        st.markdown(card_html, unsafe_allow_html=True)
                    with c_del:
                        st.write("")
                        st.write("")
                        if st.button("🗑️", key=f"del_noticia_{item['id']}", help=f"Excluir Registro Nº {num_reg_fmt}"):
                            excluir_decisao(item["id"])
                            registrar_evento(st.session_state.get("email_logado"), "excluir", "decisao", item["id"])
                            st.toast(f"Registro Nº {num_reg_fmt} excluído com sucesso!")
                            st.rerun()
                else:
                    st.markdown(card_html, unsafe_allow_html=True)




