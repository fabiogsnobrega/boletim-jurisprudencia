"""Telas administrativas: registro manual e gestão de acessos/fontes."""

from datetime import date, datetime, timedelta

import streamlit as st

from database import (
    calcular_ciclo_mensal,
    inserir_decisao,
    listar_eventos_auditoria,
    listar_fontes_oficiais,
    listar_sugestoes_fontes,
    obter_responsavel_atual,
    revisar_sugestao_fonte,
    salvar_responsavel_mes,
    verificar_status_responsavel,
)
from services.authentication import hash_senha
from services.audit import registrar_evento


def render_novo_registro(tab_novo, pode_editar: bool) -> None:
    """Renderiza o formulário de registro manual."""
    if pode_editar and tab_novo is not None:
        with tab_novo:
            st.subheader("➕ Cadastrar Nova Decisão Manualmente")
            st.caption("Inclusão manual de decisão ou alerta na base de dados.")

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
                        novo_id = inserir_decisao({
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
                        registrar_evento(st.session_state.get("email_logado"), "inserir", "decisao", novo_id)
                        st.success("Registro adicionado com sucesso! Já disponível no noticiário.")
                        st.rerun()




def render_gestao(tab_gestao, usuario_atual: str) -> None:
    """Renderiza as configurações restritas ao perfil administrador."""
    if usuario_atual == "admin" and tab_gestao is not None:
        with tab_gestao:
            st.subheader("⚙️ Painel do Administrador - Gestão do Responsável do Mês")
            st.caption(
                "Configure o e-mail e a senha do colaborador responsável por atualizar dados no ciclo mensal. "
                "A autorização vigora automaticamente do **dia 02 do mês ao dia 01 do mês subsequente**."
            )

            ciclo_sugerido_ini, ciclo_sugerido_fim = calcular_ciclo_mensal()
            ini_dt = datetime.strptime(ciclo_sugerido_ini, "%Y-%m-%d").date()
            fim_dt = datetime.strptime(ciclo_sugerido_fim, "%Y-%m-%d").date()

            resp_atual = obter_responsavel_atual()
            valido, msg_status, _ = verificar_status_responsavel()

            col_st1, col_st2 = st.columns(2)
            with col_st1:
                st.info(f"📅 **Ciclo Mensal Vigente:** {ini_dt.strftime('%d/%m/%Y')} a {fim_dt.strftime('%d/%m/%Y')}")
            with col_st2:
                if valido:
                    st.success(f"✅ **Status do Responsável:** {msg_status} ({resp_atual['email'] if resp_atual else ''})")
                else:
                    st.error(f"⚠️ **Status do Responsável:** {msg_status}")

            st.markdown("#### 👤 Cadastrar ou Atualizar Responsável do Ciclo")
            with st.form("form_responsavel_mes"):
                email_resp_def = resp_atual["email"] if resp_atual else ""
                c_r1, c_r2 = st.columns(2)
                novo_email_resp = c_r1.text_input("E-mail do Responsável:", value=email_resp_def, placeholder="nome@marcosinacio.adv.br")
                nova_senha_resp = c_r2.text_input("Senha de Acesso:", value="123", type="password")

                c_d1, c_d2 = st.columns(2)
                data_ini_input = c_d1.date_input("Início da Vigência (Dia 02):", value=ini_dt)
                data_fim_input = c_d2.date_input("Término da Vigência (Dia 01 do mês seguinte):", value=fim_dt)

                salvar_resp = st.form_submit_button("💾 Salvar e Autorizar Responsável", type="primary", use_container_width=True)

                if salvar_resp:
                    if not novo_email_resp.strip():
                        st.error("Informe o e-mail do responsável.")
                    else:
                        salvar_responsavel_mes(
                            email=novo_email_resp.strip(),
                        senha=hash_senha(nova_senha_resp.strip()),
                            data_inicio=data_ini_input.strftime("%Y-%m-%d"),
                            data_fim=data_fim_input.strftime("%Y-%m-%d"),
                        )
                        registrar_evento(st.session_state.get("email_logado"), "atualizar_responsavel", "responsavel_mes")
                        st.success("Responsável do mês atualizado com sucesso!")
                        st.rerun()

            st.divider()
            st.subheader("🔗 Endereços oficiais por tribunal")
            for tribunal_fonte, url_fonte in listar_fontes_oficiais().items():
                st.link_button(f"{tribunal_fonte} · {url_fonte}", url_fonte)

            sugestoes_pendentes = listar_sugestoes_fontes()
            st.markdown(f"#### Sugestões de atualização pendentes ({len(sugestoes_pendentes)})")
            if not sugestoes_pendentes:
                st.caption("Nenhuma sugestão pendente.")
            for sugestao in sugestoes_pendentes:
                st.markdown(
                    f"**{sugestao['tribunal']}** · {sugestao['url']}  "
                    f"\nSugerido por {sugestao.get('sugerido_por') or 'usuário não identificado'} · {sugestao['criado_em']}"
                )
                c_aceitar, c_rejeitar = st.columns(2)
                if c_aceitar.button("Aprovar novo endereço", key=f"aprovar_fonte_{sugestao['id']}"):
                    revisar_sugestao_fonte(sugestao["id"], True, st.session_state.get("email_logado"))
                    registrar_evento(st.session_state.get("email_logado"), "aprovar_fonte", "sugestao_fonte", sugestao["id"], {"tribunal": sugestao["tribunal"]})
                    st.success(f"Endereço oficial de {sugestao['tribunal']} atualizado.")
                    st.rerun()
                if c_rejeitar.button("Rejeitar sugestão", key=f"rejeitar_fonte_{sugestao['id']}"):
                    revisar_sugestao_fonte(sugestao["id"], False, st.session_state.get("email_logado"))
                    registrar_evento(st.session_state.get("email_logado"), "rejeitar_fonte", "sugestao_fonte", sugestao["id"], {"tribunal": sugestao["tribunal"]})
                    st.rerun()

        with st.expander("Histórico de ações", expanded=False):
            eventos = listar_eventos_auditoria(100)
            if eventos:
                st.dataframe(
                    [
                        {
                            "Data": evento["criado_em"],
                            "Responsável": evento["ator"] or "não identificado",
                            "Ação": evento["acao"],
                            "Registro": f"{evento['recurso']} {evento['recurso_id'] or ''}".strip(),
                        }
                        for evento in eventos
                    ],
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.caption("Nenhuma ação foi registrada ainda.")
