"""Módulo de banco de dados SQLite para o Boletim de Jurisprudência."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jurisprudencia.db"


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão ativa com o banco SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Cria a tabela de decisões e índices se não existirem."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS decisoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tribunal TEXT NOT NULL,
                tipo TEXT NOT NULL,
                identificador TEXT NOT NULL,
                titulo TEXT NOT NULL,
                ramo TEXT NOT NULL,
                status TEXT NOT NULL,
                em_alerta INTEGER NOT NULL DEFAULT 0,
                prazo_alerta TEXT,
                data_limite_verificacao TEXT,
                relator TEXT,
                orgao_julgador TEXT,
                processo_origem TEXT,
                data_evento TEXT,
                tese_resumo TEXT NOT NULL,
                conclusao_comentarios TEXT,
                link_oficial TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Migração segura para bancos existentes sem a coluna data_limite_verificacao
        cursor.execute("PRAGMA table_info(decisoes)")
        colunas = [col[1] for col in cursor.fetchall()]
        if "data_limite_verificacao" not in colunas:
            cursor.execute("ALTER TABLE decisoes ADD COLUMN data_limite_verificacao TEXT")
        conn.commit()


def inserir_decisao(dados: Dict[str, Any]) -> int:
    """Insere um novo registro de jurisprudência no banco."""
    # Garante chave data_limite_verificacao com fallback
    dados_completos = {
        "tribunal": dados.get("tribunal", "Outros"),
        "tipo": dados.get("tipo", "Informativo"),
        "identificador": dados.get("identificador", "Sem Identificação"),
        "titulo": dados.get("titulo", "Sem Título"),
        "ramo": dados.get("ramo", "Direito Administrativo"),
        "status": dados.get("status", "Em Acompanhamento"),
        "em_alerta": int(dados.get("em_alerta", 0)),
        "prazo_alerta": dados.get("prazo_alerta", "Acompanhar"),
        "data_limite_verificacao": dados.get("data_limite_verificacao"),
        "relator": dados.get("relator"),
        "orgao_julgador": dados.get("orgao_julgador"),
        "processo_origem": dados.get("processo_origem"),
        "data_evento": dados.get("data_evento"),
        "tese_resumo": dados.get("tese_resumo", ""),
        "conclusao_comentarios": dados.get("conclusao_comentarios"),
        "link_oficial": dados.get("link_oficial"),
    }

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO decisoes (
                tribunal, tipo, identificador, titulo, ramo, status,
                em_alerta, prazo_alerta, data_limite_verificacao, relator,
                orgao_julgador, processo_origem, data_evento, tese_resumo,
                conclusao_comentarios, link_oficial
            ) VALUES (
                :tribunal, :tipo, :identificador, :titulo, :ramo, :status,
                :em_alerta, :prazo_alerta, :data_limite_verificacao, :relator,
                :orgao_julgador, :processo_origem, :data_evento, :tese_resumo,
                :conclusao_comentarios, :link_oficial
            )
            """,
            dados_completos,
        )
        conn.commit()
        return cursor.lastrowid or 0


def excluir_decisao(decisao_id: int) -> bool:
    """Exclui uma decisão do banco pelo ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM decisoes WHERE id = ?", (decisao_id,))
        conn.commit()
        return cursor.rowcount > 0


def atualizar_verificacao(
    decisao_id: int,
    nova_data_limite: Optional[str] = None,
    novo_status: Optional[str] = None,
    remover_alerta: bool = False,
) -> bool:
    """Atualiza a data limite de verificação ou conclui o alerta."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if remover_alerta:
            cursor.execute(
                """
                UPDATE decisoes
                SET em_alerta = 0, status = COALESCE(?, 'Transitado em Julgado')
                WHERE id = ?
                """,
                (novo_status, decisao_id),
            )
        else:
            cursor.execute(
                """
                UPDATE decisoes
                SET data_limite_verificacao = ?, status = COALESCE(?, status)
                WHERE id = ?
                """,
                (nova_data_limite, novo_status, decisao_id),
            )
        conn.commit()
        return cursor.rowcount > 0


def listar_decisoes(
    tribunal: Optional[str] = None,
    ramo: Optional[str] = None,
    somente_alertas: bool = False,
    busca: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Consulta as decisões cadastradas com filtros opcionais."""
    query = "SELECT * FROM decisoes WHERE 1=1"
    params: List[Any] = []

    if tribunal and tribunal != "Todos":
        query += " AND tribunal = ?"
        params.append(tribunal)

    if ramo and ramo != "Todos":
        query += " AND ramo LIKE ?"
        params.append(f"%{ramo}%")

    if somente_alertas:
        query += " AND em_alerta = 1"

    if busca:
        query += """ AND (
            titulo LIKE ? OR
            identificador LIKE ? OR
            tese_resumo LIKE ? OR
            conclusao_comentarios LIKE ?
        )"""
        termo = f"%{busca}%"
        params.extend([termo, termo, termo, termo])

    query += " ORDER BY id DESC"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
