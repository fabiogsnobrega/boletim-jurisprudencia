"""Noticiário jurídico em cartões de leitura."""

from html import escape
from urllib.parse import urlsplit

import streamlit as st

from database import excluir_decisao
from modules.prazos import calcular_prazo


def _texto_html(valor) -> str:
    """Escapa valores vindos do banco antes de inseri-los no HTML dos cartões."""
    return escape(str(valor or ""), quote=True)


def _link_http_seguro(valor) -> str:
    """Aceita somente links HTTP(S) sem credenciais embutidas."""
    url = str(valor or "").strip()
    try:
        partes = urlsplit(url)
    except ValueError:
        return ""
    if partes.scheme not in {"http", "https"} or not partes.netloc or partes.username or partes.password:
        return ""
    return escape(url, quote=True)

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
                        alerta_tag = f"<span class='{classe_badge}'>{_texto_html(texto_prazo)}</span>"
                    else:
                        alerta_tag = f"<span class='badge-alerta-hoje'>🚨 ACOMPANHAR: {_texto_html(item['prazo_alerta'])}</span>"

                num_reg_fmt = f"{item['id']:02d}"

                # Construção do card no padrão editorial minimalista
                link_seguro = _link_http_seguro(item.get("link_oficial"))
                link_html = f"<div style='margin-top: 8px;'><a href='{link_seguro}' target='_blank' rel='noopener noreferrer' style='color: #263D50; font-weight: 600; text-decoration: underline;'>🔗 Consultar decisão no portal oficial →</a></div>" if link_seguro else ""
                proc_html = f"<div style='color: #4F6474; font-size: 0.88rem; margin-top: 4px;'><strong>Processo Paradigma:</strong> <code>{_texto_html(item.get('processo_origem'))}</code></div>" if item.get("processo_origem") else ""
                # Observações práticas podem conter estratégia interna; não são públicas.
                coment_html = (
                    f"<div class='comentario-box'><strong>💡 Comentários / Conclusão Prática:</strong><br>{_texto_html(item.get('conclusao_comentarios'))}</div>"
                    if pode_editar and item.get("conclusao_comentarios") else ""
                )

                card_html = (
                    f'<div class="noticia-card">'
                    f'<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">'
                    f'<div>'
                    f'<span class="badge-registro">Nº {num_reg_fmt}</span>'
                    f'<span class="badge-tribunal">{_texto_html(item.get("tribunal"))}</span>'
                    f'<span class="badge-ramo">{_texto_html(item.get("ramo"))}</span>'
                    f'<span class="badge-status">{_texto_html(item.get("status"))}</span>'
                    f'</div>'
                    f'<div>{alerta_tag}</div>'
                    f'</div>'
                    f'<h3 class="noticia-title">{_texto_html(item.get("titulo"))}</h3>'
                    f'<div style="color: #4F6474; font-size: 0.9rem; margin-bottom: 8px;">'
                    f'<strong>{_texto_html(item.get("identificador"))}</strong> • {_texto_html(item.get("tipo"))} • '
                    f'Órgão: <em>{_texto_html(item.get("orgao_julgador") or "N/A")}</em> • '
                    f'Relator: <em>{_texto_html(item.get("relator") or "N/A")}</em> • '
                    f'Data: <em>{_texto_html(item.get("data_evento") or "N/A")}</em>'
                    f'</div>'
                    f'{proc_html}'
                    f'<div class="tese-box"><strong>📌 Tese / Decisão:</strong><br>{_texto_html(item.get("tese_resumo"))}</div>'
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
                            excluir_decisao(item["id"], ator=st.session_state.get("email_logado"))
                            st.toast(f"Registro Nº {num_reg_fmt} excluído com sucesso!")
                            st.rerun()
                else:
                    st.markdown(card_html, unsafe_allow_html=True)




