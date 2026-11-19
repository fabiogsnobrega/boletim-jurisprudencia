"""Aplicação Web Streamlit - Portal de Notícias e Radar de Alertas de Jurisprudência.
Identidade visual e paleta de cores inspiradas no padrão institucional IDA Legal (https://www.idalegal.org/):
Azul Clássico (#122449), Dourado/Âmbar (#D89C1B), Areia/Off-White (#FCFBF8 / #FAF6ED) e tipografia Playfair Display + Inter.
"""

import os
from html import escape
from pathlib import Path

import streamlit as st
from database import (
    atualizar_senha_responsavel,
    listar_decisoes,
    listar_fila_revisao,
    verificar_status_responsavel,
)
from recovery_data import carregar_recuperacao_publica
from modules.revisao import render_review_tab
from modules.noticias import render_noticias
from modules.jurisprudencia import render_base_tabular, render_radar
from modules.importacao import render_importacao
from modules.administracao import render_gestao, render_novo_registro
from services.authentication import (
    autenticar_administrador,
    autenticar_responsavel,
    hash_senha,
    senha_precisa_migracao,
)

# 1. Configuração da Página - Menu lateral recolhido por padrão
st.set_page_config(
    page_title="Boletim de Jurisprudência | Direito Administrativo e Militar",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inicializa o banco e restaura, uma única vez, registros públicos verificados
# quando a hospedagem cria um SQLite novo e vazio.
carregar_recuperacao_publica()

# 2. Gerenciamento de Sessão de Autenticação
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None  # None (Público), "admin" ou "responsavel"
if "email_logado" not in st.session_state:
    st.session_state["email_logado"] = ""

# 3. Estilização CSS Personalizada - Padrão Editorial Minimalista
st.markdown('<style>' + (Path(__file__).parent / 'assets' / 'style.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)

# 4. Cabeçalho Principal Editorial
st.markdown(
    '<div class="main-header">'
    '<h1>⚖️ Boletim de Jurisprudência</h1>'
    '<p>Direito Administrativo e Militar • Tribunais Regionais e Superiores (TRF1, TRF5, TNU, STJ, STF)</p>'
    '</div>',
    unsafe_allow_html=True,
)

# 5. Barra Superior de Autenticação / Status de Sessão
usuario_atual = st.session_state["usuario_logado"]
pode_editar = usuario_atual in ["admin", "responsavel"]

# Validação automática da vigência do responsável do mês
if usuario_atual == "responsavel":
    valido, msg_val, _ = verificar_status_responsavel()
    if not valido:
        st.session_state["usuario_logado"] = None
        st.session_state["email_logado"] = ""
        st.error(f"Sua sessão expirou: {msg_val}")
        st.rerun()

# Exibição do banner do usuário ou botão discreto de login
if usuario_atual == "admin":
    c_user, c_btn = st.columns([0.85, 0.15])
    with c_user:
        st.markdown(
            f"<div class='auth-banner-admin'>👑 <strong>Administrador Conectado:</strong> {escape(str(st.session_state['email_logado']), quote=True)} (Acesso Irrestrito)</div>",
            unsafe_allow_html=True,
        )
    with c_btn:
        if st.button("🚪 Sair (Logout)", key="logout_admin", use_container_width=True):
            st.session_state["usuario_logado"] = None
            st.session_state["email_logado"] = ""
            st.rerun()

    # Alerta caso o responsável do ciclo esteja pendente de renovação
    resp_valido, resp_msg, _ = verificar_status_responsavel()
    if not resp_valido:
        st.warning(
            f"⚠️ **AVISO AO ADMINISTRADOR:** O Responsável do Mês requer atenção: **{resp_msg}**. "
            "Acesse a aba **'⚙️ Gestão de Acessos'** para cadastrar ou renovar a autorização do período."
        )

elif usuario_atual == "responsavel":
    c_user, c_btn = st.columns([0.85, 0.15])
    with c_user:
        _, msg_vig, _ = verificar_status_responsavel()
        st.markdown(
            f"<div class='auth-banner-resp'>👤 <strong>Responsável do Mês:</strong> {escape(str(st.session_state['email_logado']), quote=True)} | {escape(str(msg_vig), quote=True)}</div>",
            unsafe_allow_html=True,
        )
    with c_btn:
        if st.button("🚪 Sair (Logout)", key="logout_resp", use_container_width=True):
            st.session_state["usuario_logado"] = None
            st.session_state["email_logado"] = ""
            st.rerun()
else:
    with st.expander("🔐 Área Restrita (Login Administrativo)", expanded=False):
        st.caption("Acesse com suas credenciais para editar dados, alterar prazos de acompanhamento ou importar boletins.")
        c_p1, c_p2, c_p3 = st.columns([1, 1.2, 1])
        with c_p1:
            tipo_login = st.radio("Perfil de Acesso:", ["Administrador", "Responsável do Mês"], horizontal=True)
        with c_p2:
            login_email = st.text_input("E-mail institucional:", placeholder="seu.email@marcosinacio.adv.br")
        with c_p3:
            login_senha = st.text_input("Senha:", type="password")

        if st.button("🔑 Ingressar no Sistema", type="primary"):
            email_limpo = login_email.strip().lower()
            senha_limpa = login_senha.strip()

            if tipo_login == "Administrador":
                try:
                    admin_email = st.secrets.get("admin_email", os.getenv("BOLETIM_ADMIN_EMAIL", ""))
                    admin_senha = st.secrets.get("admin_password", os.getenv("BOLETIM_ADMIN_PASSWORD", ""))
                except Exception:
                    admin_email = os.getenv("BOLETIM_ADMIN_EMAIL", "")
                    admin_senha = os.getenv("BOLETIM_ADMIN_PASSWORD", "")

                if autenticar_administrador(email_limpo, senha_limpa, admin_email, admin_senha):
                    st.session_state["usuario_logado"] = "admin"
                    st.session_state["email_logado"] = admin_email
                    st.success("Autenticação realizada com sucesso!")
                    st.rerun()
                elif not admin_email or not admin_senha:
                    st.error("Configure admin_email e admin_password nos secrets locais ou do serviço de hospedagem.")
                else:
                    st.error("E-mail ou senha de Administrador inválidos.")
            else:
                valido, msg_val, resp = verificar_status_responsavel()
                if not resp:
                    st.error("Nenhum responsável do mês cadastrado. Solicite a liberação ao Administrador.")
                elif not valido:
                    st.error(f"Acesso negado: {msg_val}")
                elif autenticar_responsavel(email_limpo, senha_limpa, resp):
                    if senha_precisa_migracao(resp["senha"]):
                        atualizar_senha_responsavel(resp["id"], hash_senha(senha_limpa), ator=email_limpo)
                    st.session_state["usuario_logado"] = "responsavel"
                    st.session_state["email_logado"] = email_limpo
                    st.success(f"Acesso liberado como Responsável do Mês ({msg_val})!")
                    st.rerun()
                else:
                    st.error("E-mail ou senha de Responsável do Mês incorretos.")

# 6. Barra Lateral - Filtros
st.sidebar.header("🔍 Filtros de Consulta")
st.sidebar.caption("Clique no ícone '>' no topo esquerdo para recolher ou abrir este painel a qualquer momento.")

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

# Consulta dos registros disponíveis no banco local da instalação.
todas_decisoes = listar_decisoes(ordem="recentes")
decisoes_filtradas = listar_decisoes(
    tribunal=filtro_tribunal,
    ramo=filtro_ramo,
    busca=busca_texto if busca_texto else None,
    ordem="recentes",
)
alertas = [d for d in todas_decisoes if d["em_alerta"] == 1]
transitados = [d for d in todas_decisoes if "Transitado" in d["status"]]

# 7. Métricas Rápidas
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Total de Registros", len(todas_decisoes))
with col_m2:
    st.metric("🚨 Em Acompanhamento", len(alertas))
with col_m3:
    st.metric("✅ Transitados em Julgado", len(transitados))
with col_m4:
    st.metric("Resultados no Filtro", len(decisoes_filtradas))

if pode_editar:
    qtd_pendentes = len(listar_fila_revisao())
    if qtd_pendentes:
        st.info(f"📋 Você tem {qtd_pendentes} decisão(ões) aguardando revisão. Abra a aba Revisão para aceitar ou rejeitar.")

st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# 8. Definição Dinâmica das Abas por Perfil
abas_nomes = ["📰 Noticiário Jurídico", f"🚨 Radar de Alertas ({len(alertas)})"]

if pode_editar:
    abas_nomes.append("➕ Novo Registro Manual")

if pode_editar:
    abas_nomes.append("📥 Importar Boletim (Fonte oficial / PDF / texto)")

abas_nomes.append("📊 Base Tabular & Exportação")

if usuario_atual == "admin":
    abas_nomes.append("⚙️ Gestão de Acessos")

if pode_editar:
    pendencias_revisao = listar_fila_revisao()
    abas_nomes.append("📋 Revisão")

if st.session_state.get("aba_principal_selecionada") not in abas_nomes:
    st.session_state.pop("aba_principal_selecionada", None)
abas_obj = st.tabs(abas_nomes, key="aba_principal_selecionada", on_change="rerun")
idx_aba = 0

tab_noticias = abas_obj[idx_aba]
idx_aba += 1

tab_alertas = abas_obj[idx_aba]
idx_aba += 1

tab_novo = None
if pode_editar:
    tab_novo = abas_obj[idx_aba]
    idx_aba += 1

tab_importar = None
if pode_editar:
    tab_importar = abas_obj[idx_aba]
    idx_aba += 1

tab_tabela = abas_obj[idx_aba]
idx_aba += 1

tab_gestao = None
if usuario_atual == "admin":
    tab_gestao = abas_obj[idx_aba]
    idx_aba += 1

tab_revisao = None
if pode_editar:
    tab_revisao = abas_obj[idx_aba]


render_noticias(tab_noticias, decisoes_filtradas, pode_editar)


render_radar(
    tab_alertas,
    filtro_tribunal,
    filtro_ramo,
    busca_texto,
    pode_editar,
)


render_importacao(tab_importar, pode_editar)


try:
    render_review_tab(tab_revisao, pode_editar, usuario_atual == "admin")
except TypeError:
    render_review_tab(tab_revisao, pode_editar)


render_base_tabular(tab_tabela, todas_decisoes, pode_editar)


render_novo_registro(tab_novo, pode_editar)


render_gestao(tab_gestao, usuario_atual)
