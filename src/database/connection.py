"""Conexão SQLite e criação/migração do esquema local."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "jurisprudencia.db"

FONTES_OFICIAIS_PADRAO = {
    "TRF1": "https://www.trf1.jus.br/trf1/pesquisa/boletim-informativo-de-jurisprudencia",
    "TRF5": "https://www5.trf5.jus.br/boletins/jurisprudencia/",
    "TNU": "https://www.cjf.jus.br/cjf/corregedoria-da-justica-federal/turma-nacional-de-uniformizacao/boletim-tnu",
}


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão ativa com o banco SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Cria tabelas de decisões, índice e controle de responsáveis."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Tabela principal de decisões
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
                texto_original TEXT,
                hash TEXT,
                usuario_importacao TEXT,
                origem_boletim TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Migração segura para colunas adicionais se a tabela já existia
        cursor.execute("PRAGMA table_info(decisoes)")
        colunas_decisoes = {col[1] for col in cursor.fetchall()}

        colunas_novas = {
            "texto_original": "TEXT",
            "hash": "TEXT",
            "usuario_importacao": "TEXT",
            "origem_boletim": "TEXT",
            "data_limite_verificacao": "TEXT",
        }

        for coluna, tipo in colunas_novas.items():
            if coluna not in colunas_decisoes:
                cursor.execute(f"ALTER TABLE decisoes ADD COLUMN {coluna} {tipo}")

        # Índice único para evitar duplicidade de decisões pelo hash
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_decisoes_hash ON decisoes(hash);")

        # Tabela de controle do Responsável do Mês
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS responsavel_mes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                senha TEXT NOT NULL,
                data_inicio TEXT NOT NULL,
                data_fim TEXT NOT NULL,
                ativo INTEGER DEFAULT 1,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fila_revisao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dados_json TEXT NOT NULL,
                origem TEXT,
                documento TEXT,
                status TEXT NOT NULL DEFAULT 'pendente',
                comentario_usuario TEXT,
                criado_por TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revisado_por TEXT,
                revisado_em TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fontes_recentes (
                url TEXT PRIMARY KEY,
                tribunal TEXT,
                candidatos_extraidos INTEGER NOT NULL DEFAULT 0,
                verificado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fontes_oficiais (
                tribunal TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sugestoes_fontes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tribunal TEXT NOT NULL,
                url TEXT NOT NULL,
                sugerido_por TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'pendente',
                revisado_por TEXT,
                revisado_em TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ator TEXT,
                acao TEXT NOT NULL,
                recurso TEXT NOT NULL,
                recurso_id TEXT,
                detalhes_json TEXT NOT NULL DEFAULT '{}',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        for tribunal, url in FONTES_OFICIAIS_PADRAO.items():
            cursor.execute(
                "INSERT OR IGNORE INTO fontes_oficiais (tribunal, url) VALUES (?, ?)",
                (tribunal, url),
            )

        conn.commit()
