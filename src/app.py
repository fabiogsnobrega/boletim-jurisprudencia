"""Aplicação Web Streamlit - Portal de Notícias e Radar de Alertas de Jurisprudência."""

import io
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
from database import (
    atualizar_verificacao,
    excluir_decisao,
    init_db,
    inserir_decisao,
    listar_decisoes,
)
from extractor import (
    detectar_tribunal,
    extrair_decisoes_de_texto,
    extrair_texto_pdf,
)

# 1. Configuração da Página
st.set_page_config(
    page_title="Boletim de Jurisprudência",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializa o banco de dados
init_db()

# 2. Estilização CSS Personalizada
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
    }
    .badge-tribunal {
        background-color: #1e3a8a;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-right: 8px;
    }
    .badge-ramo {
        background-color: #047857;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.85rem;
        display: inline-block;
        margin-right: 8px;
    }
    .badge-status {
        background-color: #374151;
        color: #f3f4f6;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-alerta-vencido {
        background-color: #b91c1c;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-alerta-hoje {
        background-color: #d97706;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-alerta-em-dia {
        background-color: #2563eb;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        display: inline-block;
    }
    .tese-box {
        background-color: #f8fafc;
        border-left: 5px solid #3b82f6;
        padding: 14px 18px;
        border-radius: 6px;
        margin: 12px 0;
        color: #1e293b;
        font-size: 0.98rem;
        line-height: 1.5;
    }
    .comentario-box {
        background-color: #f0fdf4;
        border-left: 5px solid #10b981;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 10px 0;
        color: #065f46;
        font-size: 0.95rem;
    }
    .alerta-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Cabeçalho Principal
st.markdown(
    """
    <div class="main-header">
        <h1 style='margin:0; font-size: 2.2rem;'>⚖️ Boletim de Jurisprudência</h1>
        <p style='margin: 6px 0 0 0; opacity: 0.9; font-size: 1.1rem;'>
            Direito Administrativo e Militar • STF, STJ, TRF1, TRF5 e TNU
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# 4. Barra Lateral - Filtros
st.sidebar.header("🔍 Filtros de Busca")

busca_texto = st.sidebar.text_input(
    "Pesquisar palavra-chave:",
    placeholder="Ex.: militar, concurso, aposentadoria, BEPATA...",
)

filtro_tribunal = st.sidebar.selectbox(
    "Tribunal:",
    ["Todos", "STF", "STJ", "TRF1", "TRF5", "TNU"],
)

filtro_ramo = st.sidebar.selectbox(
    "Ramo do Direito:",
    ["Todos", "Administrativo", "Militar", "Servidor Público", "Concurso Público", "Previdenciário"],
)

# Consulta dos registros
todas_decisoes = listar_decisoes()
decisoes_filtradas = listar_decisoes(
    tribunal=filtro_tribunal,
    ramo=filtro_ramo,
    busca=busca_texto if busca_texto else None,
)
alertas = [d for d in todas_decisoes if d["em_alerta"] == 1]
transitados = [d for d in todas_decisoes if "Transitado" in d["status"]]

# 5. Métricas Rápidas
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Total de Registros", len(todas_decisoes))
with col_m2:
    st.metric("🚨 Em Acompanhamento", len(alertas))
with col_m3:
    st.metric("✅ Transitados em Julgado", len(transitados))
with col_m4:
    st.metric("Resultados no Filtro", len(decisoes_filtradas))

st.markdown("---")

# 6. Abas da Aplicação
tab_noticias, tab_alertas, tab_importar, tab_tabela, tab_novo = st.tabs([
    "📰 Noticiário Jurídico",
    f"🚨 Radar de Alertas ({len(alertas)})",
    "📥 Importar Boletim (PDF / Texto)",
    "📊 Base Tabular & Exportação",
    "➕ Novo Registro Manual",
])


def calcular_prazo(data_limite_str: str) -> tuple[int, str, str]:
    """Calcula quantos dias faltam para a data limite e retorna o status formatado."""
    hoje = date.today()
    try:
        limite = datetime.strptime(data_limite_str, "%Y-%m-%d").date()
        dias = (limite - hoje).days
        data_formatada = limite.strftime("%d/%m/%Y")

        if dias < 0:
            return dias, f"⚠️ VENCIDO há {abs(dias)} dia(s) (em {data_formatada})", "badge-alerta-vencido"
        elif dias == 0:
            return dias, f"🔔 VENCE HOJE! (em {data_formatada})", "badge-alerta-hoje"
        else:
            return dias, f"⏱️ Faltam {dias} dia(s) para verificar (até {data_formatada})", "badge-alerta-em-dia"
    except Exception:
        return 0, f"⏱️ Prazo: {data_limite_str}", "badge-alerta-em-dia"


# -------------------------------------------------------------
# ABA 1: NOTICIÁRIO JURÍDICO
# -------------------------------------------------------------
with tab_noticias:
    st.subheader("📰 Notícias e Teses Consolidadas")
    st.caption("Visão estruturada dos boletins oficiais com destaques, teses e comentários práticos.")

    if not decisoes_filtradas:
        st.info("Nenhuma decisão encontrada com os filtros selecionados.")
    else:
        for item in decisoes_filtradas:
            with st.container():
                c_card, c_del = st.columns([0.9, 0.1])
                with c_card:
                    alerta_tag = ""
                    if item["em_alerta"]:
                        if item.get("data_limite_verificacao"):
                            _, texto_prazo, classe_badge = calcular_prazo(item["data_limite_verificacao"])
                            alerta_tag = f"<span class='{classe_badge}'>{texto_prazo}</span>"
                        else:
                            alerta_tag = f"<span class='badge-alerta-hoje'>🚨 ACOMPANHAR: {item['prazo_alerta']}</span>"

                    st.markdown(
                        f"""
                        <div style="margin-top: 15px;">
                            <span class="badge-tribunal">{item['tribunal']}</span>
                            <span class="badge-ramo">{item['ramo']}</span>
                            <span class="badge-status">{item['status']}</span>
                            {alerta_tag}
                        </div>
                        <h3 style="margin: 8px 0 4px 0; color: #1e293b;">{item['titulo']}</h3>
                        <div style="color: #64748b; font-size: 0.9rem; margin-bottom: 8px;">
                            <strong>{item['identificador']}</strong> • {item['tipo']} • 
                            Órgão: <em>{item['orgao_julgador'] or 'N/A'}</em> • 
                            Relator: <em>{item['relator'] or 'N/A'}</em> • 
                            Data: <em>{item['data_evento'] or 'N/A'}</em>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if item["processo_origem"]:
                        st.caption(f"📁 Processo(s) paradigma: `{item['processo_origem']}`")

                    st.markdown(
                        f"""
                        <div class="tese-box">
                            <strong>📌 Tese / Decisão:</strong><br>
                            {item['tese_resumo']}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if item["conclusao_comentarios"]:
                        st.markdown(
                            f"""
                            <div class="comentario-box">
                                <strong>💡 Comentários / Conclusão Prática:</strong><br>
                                {item['conclusao_comentarios']}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    if item["link_oficial"]:
                        st.markdown(f"[🔗 Consultar no portal oficial]({item['link_oficial']})")

                with c_del:
                    st.write("")
                    st.write("")
                    if st.button("🗑️", key=f"del_noticia_{item['id']}", help="Excluir esta decisão"):
                        excluir_decisao(item["id"])
                        st.toast("Decisão excluída com sucesso!")
                        st.rerun()

                st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px dashed #cbd5e1;'/>", unsafe_allow_html=True)


# -------------------------------------------------------------
# ABA 2: RADAR DE ALERTAS (COM DIAS RESTANTES)
# -------------------------------------------------------------
with tab_alertas:
    st.subheader("🚨 Painel de Acompanhamento e Prazos")
    st.warning(
        "Estes processos e temas estão **afetados, em julgamento ou pendentes de trânsito em julgado**. "
        "Acompanhe abaixo quantos dias faltam para a nova verificação de cada um."
    )

    alertas_lista = [d for d in decisoes_filtradas if d["em_alerta"] == 1]

    if not alertas_lista:
        st.success("Não há nenhum alerta pendente para os filtros selecionados!")
    else:
        for item in alertas_lista:
            data_limite_str = item.get("data_limite_verificacao") or date.today().strftime("%Y-%m-%d")
            dias_restantes, texto_prazo, classe_badge = calcular_prazo(data_limite_str)

            borda_cor = "#ef4444" if dias_restantes <= 0 else "#3b82f6"

            with st.container():
                st.markdown(
                    f"""
                    <div class="alerta-card" style="border: 2px solid {borda_cor};">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <span class="badge-tribunal">{item['tribunal']}</span>
                                <span class="badge-ramo">{item['ramo']}</span>
                                <span style="background-color: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.85rem;">
                                    Status: {item['status']}
                                </span>
                            </div>
                            <span class="{classe_badge}">
                                {texto_prazo}
                            </span>
                        </div>
                        <h3 style="margin-top: 12px; color: #111827;">{item['identificador']} - {item['titulo']}</h3>
                        <p style="color: #4b5563; margin-bottom: 8px;">
                            <strong>Processo(s):</strong> {item['processo_origem'] or 'N/A'} | 
                            <strong>Órgão:</strong> {item['orgao_julgador'] or 'N/A'} | 
                            <strong>Data do Evento:</strong> {item['data_evento'] or 'N/A'}
                        </p>
                        <div class="tese-box" style="margin-top: 10px;">
                            <strong>Questão em debate / Tese:</strong><br>
                            {item['tese_resumo']}
                        </div>
                        <div class="comentario-box">
                            <strong>Orientação para acompanhamento:</strong><br>
                            {item['conclusao_comentarios'] or 'Acompanhar nova movimentação processual.'}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Ações rápidas no card de alerta
                col_act1, col_act2, col_act3, col_act4 = st.columns([1, 1, 1.2, 0.8])
                with col_act1:
                    if st.button("➕ Adiar 15 dias", key=f"adiar15_{item['id']}"):
                        nova_data = (date.today() + timedelta(days=15)).strftime("%Y-%m-%d")
                        atualizar_verificacao(item["id"], nova_data_limite=nova_data)
                        st.toast("Verificação adiada em 15 dias!")
                        st.rerun()
                with col_act2:
                    if st.button("➕ Adiar 30 dias", key=f"adiar30_{item['id']}"):
                        nova_data = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
                        atualizar_verificacao(item["id"], nova_data_limite=nova_data)
                        st.toast("Verificação adiada em 30 dias!")
                        st.rerun()
                with col_act3:
                    if st.button("✅ Concluir / Transitou", key=f"transitou_{item['id']}"):
                        atualizar_verificacao(item["id"], remover_alerta=True, novo_status="Transitado em Julgado")
                        st.toast("Alerta concluído e marcado como Transitado em Julgado!")
                        st.rerun()
                with col_act4:
                    if st.button("🗑️ Excluir", key=f"del_alerta_{item['id']}"):
                        excluir_decisao(item["id"])
                        st.toast("Decisão excluída!")
                        st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)


# -------------------------------------------------------------
# ABA 3: IMPORTAR BOLETIM (PDF OU TEXTO AUTOMÁTICO)
# -------------------------------------------------------------
with tab_importar:
    st.subheader("📥 Importação Automática de Boletim")
    st.caption("Faça upload de um arquivo PDF ou cole o texto do boletim. O sistema lerá e extrairá as decisões automaticamente.")

    formato_importacao = st.radio(
        "Escolha a forma de importação:",
        ["📄 Upload de Arquivo PDF", "📋 Colar Texto do Boletim"],
        horizontal=True,
    )

    texto_para_processar = ""
    tribunal_sugerido = "TRF1"

    if formato_importacao == "📄 Upload de Arquivo PDF":
        arquivo_pdf = st.file_uploader("Selecione o arquivo PDF do Boletim:", type=["pdf"])
        if arquivo_pdf is not None:
            bytes_pdf = arquivo_pdf.read()
            with st.spinner("Lendo arquivo PDF e extraindo texto..."):
                texto_para_processar = extrair_texto_pdf(bytes_pdf)
                tribunal_sugerido = detectar_tribunal(texto_para_processar)
            st.success(f"PDF lido com sucesso! ({len(texto_para_processar)} caracteres extraídos). Tribunal sugerido: **{tribunal_sugerido}**.")
    else:
        texto_para_processar = st.text_area(
            "Cole aqui o conteúdo do boletim informativo ou clipping:",
            height=200,
            placeholder="Cole aqui o texto do boletim (ex: STF, TRF1, STJ...)",
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
        apenas_adm_militar = st.checkbox(
            "🎯 Filtrar apenas decisões de Direito Administrativo e Militar",
            value=True,
            help="Desmarque se quiser extrair todas as decisões do boletim independente da matéria.",
        )

    if st.button("⚡ Ler Boletim e Extrair Decisões", type="primary", use_container_width=True):
        if not texto_para_processar.strip():
            st.error("Por favor, faça o upload de um PDF ou cole o texto do boletim antes de extrair.")
        else:
            with st.spinner("Analisando estrutura, identificando teses e prazos..."):
                candidatos = extrair_decisoes_de_texto(
                    texto_para_processar,
                    tribunal_padrao=tribunal_escolhido,
                    apenas_adm_militar=apenas_adm_militar,
                )
                st.session_state["decisoes_extraidas_temp"] = candidatos

    if "decisoes_extraidas_temp" in st.session_state and st.session_state["decisoes_extraidas_temp"]:
        candidatos = st.session_state["decisoes_extraidas_temp"]
        st.markdown(f"### 📋 Decisões Identificadas ({len(candidatos)})")
        st.info("Revise as decisões encontradas abaixo antes de salvar na base.")

        for i, cand in enumerate(candidatos):
            with st.expander(f"{cand['identificador']} - {cand['titulo']} ({cand['status']})", expanded=True):
                st.write(f"**Tribunal:** {cand['tribunal']} | **Ramo:** {cand['ramo']}")
                st.write(f"**Processo:** {cand['processo_origem'] or 'N/A'} | **Data:** {cand['data_evento']}")
                st.write(f"**Status:** {cand['status']}")
                if cand["em_alerta"]:
                    st.warning(f"🚨 Será cadastrado no Painel de Alertas: {cand['prazo_alerta']}")
                st.write("**Tese / Síntese:**")
                st.write(cand["tese_resumo"])
                if cand["conclusao_comentarios"]:
                    st.write("**Comentários:**", cand["conclusao_comentarios"])

        col_salvar, col_limpar = st.columns([2, 1])
        with col_salvar:
            if st.button("💾 Confirmar e Salvar Todas na Base", type="primary", use_container_width=True):
                qtd_salva = 0
                for cand in candidatos:
                    inserir_decisao(cand)
                    qtd_salva += 1
                del st.session_state["decisoes_extraidas_temp"]
                st.success(f"{qtd_salva} decisões foram salvas com sucesso no banco de dados!")
                st.rerun()
        with col_limpar:
            if st.button("❌ Descartar Extração", use_container_width=True):
                del st.session_state["decisoes_extraidas_temp"]
                st.rerun()


# -------------------------------------------------------------
# ABA 4: BASE TABULAR & EXPORTAÇÃO
# -------------------------------------------------------------
with tab_tabela:
    st.subheader("📊 Base de Dados Estruturada")
    st.caption("Consulte a tabela completa, remova registros indesejados ou faça a exportação.")

    if todas_decisoes:
        df = pd.DataFrame(todas_decisoes)
        colunas_exibicao = [
            "id", "tribunal", "identificador", "titulo", "ramo",
            "status", "em_alerta", "data_limite_verificacao", "data_evento", "processo_origem"
        ]
        st.dataframe(df[colunas_exibicao], use_container_width=True)

        # Exclusão rápida por ID
        with st.expander("🗑️ Excluir Registro por ID"):
            col_id, col_btn_del = st.columns([2, 1])
            id_para_excluir = col_id.selectbox(
                "Selecione o registro para excluir:",
                options=[d["id"] for d in todas_decisoes],
                format_func=lambda x: f"ID {x} - {[d['identificador'] for d in todas_decisoes if d['id'] == x][0]} - {[d['titulo'] for d in todas_decisoes if d['id'] == x][0]}",
            )
            if col_btn_del.button("Confirmar Exclusão", type="secondary"):
                excluir_decisao(id_para_excluir)
                st.toast(f"Registro ID {id_para_excluir} excluído!")
                st.rerun()

        col_exp1, col_exp2 = st.columns(2)

        # Exportar CSV
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        col_exp1.download_button(
            label="📥 Exportar Base Completa em CSV",
            data=csv_data,
            file_name=f"boletim_jurisprudencia_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
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
            use_container_width=True,
        )
    else:
        st.info("A base está vazia.")


# -------------------------------------------------------------
# ABA 5: NOVO REGISTRO MANUAL
# -------------------------------------------------------------
with tab_novo:
    st.subheader("➕ Cadastrar Nova Decisão Manualmente")
    st.caption("Caso deseje incluir uma decisão pontual sem importar boletim.")

    with st.form("form_novo_registro", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        novo_tribunal = c1.selectbox("Tribunal", ["STF", "STJ", "TRF1", "TRF5", "TNU", "TRU5"])
        novo_tipo = c2.selectbox(
            "Tipo",
            ["Tema de Repercussão Geral", "Recurso Repetitivo", "Julgado de Turma", "Informativo", "Outros"]
        )
        novo_identificador = c3.text_input("Identificador", placeholder="Ex: Tema 1480 ou REsp 123456")

        c4, c5 = st.columns([2, 1])
        novo_titulo = c4.text_input("Título / Assunto Principal", placeholder="Ex: Adicional de insalubridade para servidores...")
        novo_ramo = c5.text_input("Ramo do Direito", value="Direito Administrativo / Servidor Público")

        c6, c7, c8 = st.columns(3)
        novo_status = c6.selectbox(
            "Status",
            ["Transitado em Julgado", "Acórdão Publicado", "Em Julgamento", "Afetado / Pendente", "Sem Repercussão Geral"]
        )
        novo_em_alerta = c7.checkbox("🚨 Ativar no Painel de Alertas?", value=False)
        nova_data_limite = c8.date_input(
            "Data Limite da Nova Verificação",
            value=date.today() + timedelta(days=20),
        )

        c9, c10, c11 = st.columns(3)
        novo_relator = c9.text_input("Relator(a)")
        novo_orgao = c10.text_input("Órgão Julgador", placeholder="Ex: Primeira Seção, Segunda Turma...")
        novo_proc_origem = c11.text_input("Processo Origem / Paradigma")

        novo_data = st.text_input("Data do Evento", value=datetime.now().strftime("%d/%m/%Y"))
        nova_tese = st.text_area("Tese Firmada / Resumo da Decisão", height=100)
        novo_comentario = st.text_area("Comentários Práticos / Conclusão", height=80)
        novo_link = st.text_input("Link Oficial")

        submetido = st.form_submit_button("Salvar Registro", use_container_width=True)

        if submetido:
            if not novo_identificador or not novo_titulo or not nova_tese:
                st.error("Por favor, preencha pelo menos o Identificador, Título e a Tese.")
            else:
                data_limite_fmt = nova_data_limite.strftime("%Y-%m-%d") if novo_em_alerta else None
                inserir_decisao({
                    "tribunal": novo_tribunal,
                    "tipo": novo_tipo,
                    "identificador": novo_identificador,
                    "titulo": novo_titulo,
                    "ramo": novo_ramo,
                    "status": novo_status,
                    "em_alerta": 1 if novo_em_alerta else 0,
                    "prazo_alerta": f"Até {nova_data_limite.strftime('%d/%m/%Y')}" if novo_em_alerta else "Concluído",
                    "data_limite_verificacao": data_limite_fmt,
                    "relator": novo_relator,
                    "orgao_julgador": novo_orgao,
                    "processo_origem": novo_proc_origem,
                    "data_evento": novo_data,
                    "tese_resumo": nova_tese,
                    "conclusao_comentarios": novo_comentario,
                    "link_oficial": novo_link,
                })
                st.success("Registro adicionado com sucesso! Já disponível no noticiário.")
                st.rerun()
