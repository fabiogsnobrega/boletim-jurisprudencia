"""Operações de leitura e escrita dos repositórios SQLite."""

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from .connection import get_connection
from .models import DecisionData


def calcular_hash_decisao(dados: DecisionData) -> str:
    """Calcula o hash SHA-256 único de uma decisão judicial para controle de duplicidade."""
    tribunal = str(dados.get("tribunal") or "").strip().lower()
    processo = str(dados.get("processo_origem") or dados.get("identificador") or "").strip().lower()
    titulo = str(dados.get("titulo") or "").strip().lower()
    texto = str(dados.get("texto_original") or dados.get("tese_resumo") or "").strip()
    raw = f"{tribunal}|{processo}|{titulo}|{texto}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def registrar_evento_auditoria(
    ator: Optional[str],
    acao: str,
    recurso: str,
    recurso_id: Optional[str] = None,
    detalhes: Optional[Dict[str, Any]] = None,
) -> int:
    """Grava um evento administrativo sem copiar textos ou observações do usuário."""
    detalhes_json = json.dumps(detalhes or {}, ensure_ascii=False, sort_keys=True)
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO auditoria (ator, acao, recurso, recurso_id, detalhes_json) VALUES (?, ?, ?, ?, ?)",
            (ator, acao, recurso, str(recurso_id) if recurso_id is not None else None, detalhes_json),
        )
        return int(cursor.lastrowid or 0)


def _registrar_evento_conn(conn, ator, acao, recurso, recurso_id=None, detalhes=None):
    """Grava auditoria na mesma transação SQLite da alteração correspondente."""
    cursor = conn.execute(
        "INSERT INTO auditoria (ator, acao, recurso, recurso_id, detalhes_json) VALUES (?, ?, ?, ?, ?)",
        (ator, acao, recurso, str(recurso_id) if recurso_id is not None else None,
         json.dumps(detalhes or {}, ensure_ascii=False, sort_keys=True)),
    )
    return int(cursor.lastrowid or 0)


def listar_eventos_auditoria(limite: int = 100) -> List[Dict[str, Any]]:
    """Retorna eventos recentes, limitado para não carregar o histórico inteiro."""
    limite_seguro = max(1, min(int(limite), 500))
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM auditoria ORDER BY id DESC LIMIT ?", (limite_seguro,)
        ).fetchall()
        return [dict(row) for row in rows]


def calcular_ciclo_mensal(data_ref: Optional[date] = None) -> Tuple[str, str]:
    """
    Calcula as datas de início e fim do ciclo mensal de autorização:
    O ciclo vai do dia 02 do mês atual até o dia 01 do mês seguinte.
    Se hoje for dia 01, o ciclo vigente começou no dia 02 do mês anterior.
    """
    hoje = data_ref or date.today()
    if hoje.day == 1:
        # Estamos no último dia do ciclo que começou no dia 02 do mês anterior
        mes_ant = hoje.month - 1 if hoje.month > 1 else 12
        ano_ant = hoje.year if hoje.month > 1 else hoje.year - 1
        inicio = date(ano_ant, mes_ant, 2)
        fim = hoje
    else:
        # Ciclo começou no dia 02 do mês atual e vai até o dia 01 do mês seguinte
        inicio = date(hoje.year, hoje.month, 2)
        mes_prox = hoje.month + 1 if hoje.month < 12 else 1
        ano_prox = hoje.year if hoje.month < 12 else hoje.year + 1
        fim = date(ano_prox, mes_prox, 1)

    return inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d")


def adicionar_a_fila_revisao(
    dados: DecisionData, origem: Optional[str] = None,
    documento: Optional[str] = None, criado_por: Optional[str] = None,
) -> int:
    """Guarda um candidato para revisão antes da inclusão na base oficial."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO fila_revisao (dados_json, origem, documento, criado_por) VALUES (?, ?, ?, ?)",
            (json.dumps(dados, ensure_ascii=False), origem, documento, criado_por),
        )
        _registrar_evento_conn(conn, criado_por, "enfileirar_candidato", "fila_revisao", cursor.lastrowid,
                               {"origem": origem, "documento": documento})
        return cursor.lastrowid or 0


def listar_fila_revisao(status: str = "pendente", duplicatas_primeiro: bool = True) -> List[Dict[str, Any]]:
    """Retorna itens da fila com detecção de causa da duplicidade e ordenação prioritária."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM fila_revisao WHERE status = ? ORDER BY id ASC", (status,)
        ).fetchall()
        resultado = []
        for row in rows:
            item = dict(row)
            item["dados"] = json.loads(item.pop("dados_json"))
            item["_duplicata"] = False
            item["_motivo_duplicata"] = ""
            resultado.append(item)

        if not duplicatas_primeiro or not resultado:
            return resultado

        # Identificação de duplicatas por CNJ ou hash
        grupos_processo: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for item in resultado:
            dados = item["dados"]
            numero = str(dados.get("processo_origem") or dados.get("identificador") or "")
            match = re.search(r"\d{7}-\d{2}\.\d{4}\.4\.\d{2}\.\d{4}", numero)
            tribunal = str(dados.get("tribunal") or "").strip().lower()
            if match:
                chave = (tribunal, match.group(0))
                grupos_processo.setdefault(chave, []).append(item)

        for (tribunal, num_proc), grupo in grupos_processo.items():
            if len(grupo) > 1:
                docs = {g.get("documento") or g.get("origem") for g in grupo}
                if len(docs) == 1 and None not in docs and "" not in docs:
                    motivo = "Documento repetido: o mesmo boletim foi enviado mais de uma vez ou o processo foi citado duas vezes no mesmo boletim"
                else:
                    motivo = "Processo repetido: o mesmo número CNJ consta em fontes ou boletins diferentes"
                for g in grupo:
                    g["_duplicata"] = True
                    g["_motivo_duplicata"] = motivo

        # Ordena trazendo as duplicadas no início da fila
        resultado.sort(key=lambda i: (0 if i["_duplicata"] else 1, i["id"]))
        return resultado


def buscar_decisoes_correlatas(dados: dict, limite: int = 3) -> List[Dict[str, Any]]:
    """Busca na base oficial decisões já aprovadas com temas ou matérias similares."""
    ramo = dados.get("ramo")
    texto = str(dados.get("texto_original") or dados.get("tese_resumo") or "").lower()
    identificador = dados.get("identificador", "")

    palavras_chave = []
    for termo in ["militar", "concurso", "servidor", "precatório", "pensão", "reajuste", "28,86", "dano moral", "posse", "edital"]:
        if termo in texto or (ramo and termo in ramo.lower()):
            palavras_chave.append(termo)

    with get_connection() as conn:
        if palavras_chave:
            condicoes = " OR ".join(["tese_resumo LIKE ? OR titulo LIKE ?" for _ in palavras_chave[:4]])
            params: List[Any] = []
            for p in palavras_chave[:4]:
                params.extend([f"%{p}%", f"%{p}%"])
            query = f"SELECT id, tribunal, identificador, titulo, ramo, status FROM decisoes WHERE identificador != ? AND ({condicoes}) ORDER BY id DESC LIMIT ?"
            params = [identificador] + params + [limite]
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        elif ramo:
            query = "SELECT id, tribunal, identificador, titulo, ramo, status FROM decisoes WHERE identificador != ? AND ramo = ? ORDER BY id DESC LIMIT ?"
            rows = conn.execute(query, (identificador, ramo, limite)).fetchall()
            return [dict(r) for r in rows]
        return []


def atualizar_candidato(candidato_id: int, dados: DecisionData, ator: Optional[str] = None) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE fila_revisao SET dados_json = ? WHERE id = ? AND status = 'pendente'",
            (json.dumps(dados, ensure_ascii=False), candidato_id),
        )
        if cursor.rowcount:
            _registrar_evento_conn(conn, ator, "editar_candidato", "candidato", candidato_id)
        return cursor.rowcount > 0


def revisar_candidato(
    candidato_id: int, acao: str, comentario: Optional[str], revisor: Optional[str]
) -> bool:
    if acao not in ("aceita", "rejeitada"):
        raise ValueError("Ação de revisão inválida")
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE fila_revisao SET status = ?, comentario_usuario = ?, revisado_por = ?, "
            "revisado_em = CURRENT_TIMESTAMP WHERE id = ? AND status = 'pendente'",
            (acao, comentario, revisor, candidato_id),
        )
        if cursor.rowcount:
            _registrar_evento_conn(conn, revisor, f"candidato_{acao}", "candidato", candidato_id)
        return cursor.rowcount > 0


def aceitar_candidato(candidato_id: int, comentario: Optional[str], revisor: Optional[str]) -> bool:
    """Inclui a decisão e conclui a revisão na mesma transação."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT dados_json, origem, documento, criado_por FROM fila_revisao WHERE id = ? AND status = 'pendente'",
            (candidato_id,),
        ).fetchone()
        if not row:
            return False
        dados = json.loads(row["dados_json"])
        dados["conclusao_comentarios"] = comentario or None
        hash_decisao = dados.get("hash") or calcular_hash_decisao(dados)
        dados["hash"] = hash_decisao
        dados["usuario_importacao"] = revisor or row["criado_por"]
        dados["origem_boletim"] = row["documento"] or row["origem"]
        dados["em_alerta"] = int(dados.get("em_alerta") or 0)
        dados["tribunal"] = dados.get("tribunal") or "Outros"
        dados["tipo"] = dados.get("tipo") or "Informativo"
        dados["identificador"] = dados.get("identificador") or "Sem Identificação"
        dados["titulo"] = dados.get("titulo") or "Sem Título"
        dados["ramo"] = dados.get("ramo") or "Direito Administrativo"
        dados["status"] = dados.get("status") or "Em Acompanhamento"
        dados["tese_resumo"] = dados.get("tese_resumo") or ""

        campos = (
            "tribunal", "tipo", "identificador", "titulo", "ramo", "status", "em_alerta",
            "prazo_alerta", "data_limite_verificacao", "relator", "orgao_julgador",
            "processo_origem", "data_evento", "tese_resumo", "conclusao_comentarios", "link_oficial",
            "texto_original", "hash", "usuario_importacao", "origem_boletim"
        )
        valores = [dados.get(campo) for campo in campos]
        try:
            cursor = conn.execute(
                f"INSERT INTO decisoes ({', '.join(campos)}) VALUES ({', '.join('?' for _ in campos)})",
                valores,
            )
        except sqlite3.IntegrityError as exc:
            if "decisoes.hash" not in str(exc):
                raise
            conn.execute(
                "UPDATE fila_revisao SET status = 'rejeitada', comentario_usuario = ?, revisado_por = ?, "
                "revisado_em = CURRENT_TIMESTAMP WHERE id = ?",
                ("Duplicata descartada: já existe na base oficial", revisor, candidato_id),
            )
            _registrar_evento_conn(conn, revisor, "insercao_duplicada", "fila_revisao", candidato_id, {"hash": hash_decisao})
            return False
        conn.execute(
            "UPDATE fila_revisao SET status = 'aceita', comentario_usuario = ?, revisado_por = ?, "
            "revisado_em = CURRENT_TIMESTAMP WHERE id = ?",
            (comentario, revisor, candidato_id),
        )
        novo_id = cursor.lastrowid or 0
        _registrar_evento_conn(conn, revisor, "aceitar_candidato", "decisoes", novo_id,
                               {"hash": hash_decisao, "candidato_id": candidato_id})
        return True


def aceitar_candidatos_em_lote(
    candidatos_ids: List[int],
    revisor: Optional[str] = None,
    comentarios_por_id: Optional[Dict[int, str]] = None,
) -> Tuple[int, int]:
    """Aceita múltiplos candidatos em uma única transação rápida. Retorna (aceitos, duplicados)."""
    if not candidatos_ids:
        return 0, 0
    comentarios = comentarios_por_id or {}
    aceitos = 0
    duplicados = 0

    with get_connection() as conn:
        for cid in candidatos_ids:
            row = conn.execute(
                "SELECT dados_json, origem, documento, criado_por FROM fila_revisao WHERE id = ? AND status = 'pendente'",
                (cid,),
            ).fetchone()
            if not row:
                continue
            dados = json.loads(row["dados_json"])
            comentario = comentarios.get(cid) or dados.get("conclusao_comentarios")
            dados["conclusao_comentarios"] = comentario or None
            hash_decisao = dados.get("hash") or calcular_hash_decisao(dados)

            # Verifica se já existe por hash
            row_dup = conn.execute("SELECT id FROM decisoes WHERE hash = ?", (hash_decisao,)).fetchone()
            if row_dup:
                conn.execute(
                    "UPDATE fila_revisao SET status = 'rejeitada', comentario_usuario = 'Duplicata descartada automaticamente', "
                    "revisado_por = ?, revisado_em = CURRENT_TIMESTAMP WHERE id = ?",
                    (revisor, cid),
                )
                conn.execute(
                    "INSERT INTO auditoria (ator, acao, recurso, recurso_id, detalhes_json) VALUES (?, ?, ?, ?, ?)",
                    (revisor, "insercao_duplicada", "fila_revisao", str(cid), json.dumps({"hash": hash_decisao}, ensure_ascii=False)),
                )
                duplicados += 1
                continue

            dados["hash"] = hash_decisao
            dados["usuario_importacao"] = revisor or row["criado_por"]
            dados["origem_boletim"] = row["documento"] or row["origem"]
            dados["em_alerta"] = int(dados.get("em_alerta") or 0)
            dados["tribunal"] = dados.get("tribunal") or "Outros"
            dados["tipo"] = dados.get("tipo") or "Informativo"
            dados["identificador"] = dados.get("identificador") or "Sem Identificação"
            dados["titulo"] = dados.get("titulo") or "Sem Título"
            dados["ramo"] = dados.get("ramo") or "Direito Administrativo"
            dados["status"] = dados.get("status") or "Em Acompanhamento"
            dados["tese_resumo"] = dados.get("tese_resumo") or ""

            campos = (
                "tribunal", "tipo", "identificador", "titulo", "ramo", "status", "em_alerta",
                "prazo_alerta", "data_limite_verificacao", "relator", "orgao_julgador",
                "processo_origem", "data_evento", "tese_resumo", "conclusao_comentarios", "link_oficial",
                "texto_original", "hash", "usuario_importacao", "origem_boletim"
            )
            valores = [dados.get(campo) for campo in campos]
            cursor = conn.execute(
                f"INSERT INTO decisoes ({', '.join(campos)}) VALUES ({', '.join('?' for _ in campos)})",
                valores,
            )
            novo_id = cursor.lastrowid or 0
            conn.execute(
                "UPDATE fila_revisao SET status = 'aceita', comentario_usuario = ?, revisado_por = ?, "
                "revisado_em = CURRENT_TIMESTAMP WHERE id = ?",
                (comentario, revisor, cid),
            )
            conn.execute(
                "INSERT INTO auditoria (ator, acao, recurso, recurso_id, detalhes_json) VALUES (?, ?, ?, ?, ?)",
                (revisor, "aceitar_candidato", "decisoes", str(novo_id), json.dumps({"hash": hash_decisao, "candidato_id": cid}, ensure_ascii=False)),
            )
            aceitos += 1
        conn.commit()
    return aceitos, duplicados


def rejeitar_candidatos_em_lote(
    candidatos_ids: List[int],
    revisor: Optional[str] = None,
    motivo: Optional[str] = "Rejeitado em lote na revisão",
) -> int:
    """Rejeita múltiplos candidatos em uma única transação rápida."""
    if not candidatos_ids:
        return 0
    ids_limpos = sorted({int(cid) for cid in candidatos_ids})
    placeholders = ", ".join("?" for _ in ids_limpos)
    with get_connection() as conn:
        cursor = conn.execute(
            f"UPDATE fila_revisao SET status = 'rejeitada', comentario_usuario = ?, revisado_por = ?, "
            f"revisado_em = CURRENT_TIMESTAMP WHERE id IN ({placeholders}) AND status = 'pendente'",
            [motivo, revisor] + ids_limpos,
        )
        total = cursor.rowcount
        conn.execute(
            "INSERT INTO auditoria (ator, acao, recurso, detalhes_json) VALUES (?, ?, ?, ?)",
            (revisor, "rejeitar_em_lote", "fila_revisao", json.dumps({"quantidade": total, "ids": ids_limpos}, ensure_ascii=False)),
        )
        conn.commit()
        return total


def registrar_fonte_verificada(url: str, tribunal: str, quantidade: int, ator: Optional[str] = None) -> None:
    """Registra um endereço somente quando a extração encontrou candidatos."""
    if quantidade < 1:
        return
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO fontes_recentes (url, tribunal, candidatos_extraidos, verificado_em) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP) ON CONFLICT(url) DO UPDATE SET "
            "tribunal = excluded.tribunal, candidatos_extraidos = excluded.candidatos_extraidos, "
            "verificado_em = CURRENT_TIMESTAMP",
            (url, tribunal, quantidade),
        )
        _registrar_evento_conn(conn, ator, "verificar_fonte", "fonte_oficial",
                               detalhes={"tribunal": tribunal, "candidatos": quantidade})


def listar_fontes_recentes(limite: int = 8) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM fontes_recentes ORDER BY verificado_em DESC LIMIT ?", (limite,)
        ).fetchall()
        return [dict(row) for row in rows]


def listar_fontes_oficiais() -> Dict[str, str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT tribunal, url FROM fontes_oficiais ORDER BY tribunal").fetchall()
        return {row["tribunal"]: row["url"] for row in rows}


def sugerir_atualizacao_fonte(tribunal: str, url: str, usuario: Optional[str]) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO sugestoes_fontes (tribunal, url, sugerido_por) VALUES (?, ?, ?)",
            (tribunal, url.strip(), usuario),
        )
        _registrar_evento_conn(conn, usuario, "sugerir_fonte", "tribunal", detalhes={"tribunal": tribunal})
        return cursor.lastrowid or 0


def listar_sugestoes_fontes(status: str = "pendente") -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sugestoes_fontes WHERE status = ? ORDER BY id DESC", (status,)
        ).fetchall()
        return [dict(row) for row in rows]


def revisar_sugestao_fonte(sugestao_id: int, aprovar: bool, revisor: Optional[str]) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT tribunal, url FROM sugestoes_fontes WHERE id = ? AND status = 'pendente'",
            (sugestao_id,),
        ).fetchone()
        if not row:
            return False
        if aprovar:
            conn.execute(
                "INSERT INTO fontes_oficiais (tribunal, url, atualizado_em) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(tribunal) DO UPDATE SET url = excluded.url, atualizado_em = CURRENT_TIMESTAMP",
                (row["tribunal"], row["url"]),
            )
        conn.execute(
            "UPDATE sugestoes_fontes SET status = ?, revisado_por = ?, revisado_em = CURRENT_TIMESTAMP WHERE id = ?",
            ("aprovada" if aprovar else "rejeitada", revisor, sugestao_id),
        )
        _registrar_evento_conn(conn, revisor, "aprovar_fonte" if aprovar else "rejeitar_fonte",
                               "sugestao_fonte", sugestao_id, {"tribunal": row["tribunal"]})
        return True


def excluir_todas_pendencias_revisao(ator: Optional[str] = None) -> int:
    """Remove somente candidatos ainda pendentes; mantém os já revisados."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM fila_revisao WHERE status = 'pendente'")
        if cursor.rowcount:
            _registrar_evento_conn(conn, ator, "excluir_pendencias", "fila_revisao", detalhes={"removidas": cursor.rowcount})
        return cursor.rowcount


def encontrar_duplicatas_fila() -> List[List[Dict[str, Any]]]:
    """Agrupa pendências com o mesmo número CNJ e tribunal, ignorando campos inferidos."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM fila_revisao WHERE status = 'pendente' ORDER BY id ASC").fetchall()
    grupos: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        dados = json.loads(item.pop("dados_json"))
        numero = str(dados.get("processo_origem") or dados.get("identificador") or "")
        match = re.search(r"\d{7}-\d{2}\.\d{4}\.4\.\d{2}\.\d{4}", numero)
        if not match:
            continue
        dados["_tamanho_conteudo"] = len(str(dados.get("texto_original") or dados.get("tese_resumo") or ""))
        item["dados"] = dados
        chave = (" ".join(str(dados.get("tribunal") or "").casefold().split()), match.group(0))
        grupos.setdefault(chave, []).append(item)
    return [sorted(grupo, key=lambda i: (-i["dados"]["_tamanho_conteudo"], i["id"])) for grupo in grupos.values() if len(grupo) > 1]


def excluir_candidatos_fila(candidato_ids: List[int], ator: Optional[str] = None) -> int:
    ids = sorted({int(candidato_id) for candidato_id in candidato_ids})
    if not ids:
        return 0
    placeholders = ", ".join("?" for _ in ids)
    with get_connection() as conn:
        cursor = conn.execute(
            f"DELETE FROM fila_revisao WHERE status = 'pendente' AND id IN ({placeholders})", ids
        )
        if cursor.rowcount:
            _registrar_evento_conn(conn, ator, "deduplicar", "fila_revisao", detalhes={"ids": ids, "removidas": cursor.rowcount})
        return cursor.rowcount


def encontrar_grupos_duplicados() -> List[List[Dict[str, Any]]]:
    """Localiza possíveis cópias da mesma decisão usando tribunal e número CNJ."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM decisoes ORDER BY id ASC").fetchall()
    grupos: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    def normalizar(valor: Any) -> str:
        return " ".join(str(valor or "").casefold().split())

    for row in rows:
        item = dict(row)
        numero = str(item.get("processo_origem") or item.get("identificador") or "")
        match = re.search(r"\d{7}-\d{2}\.\d{4}\.4\.\d{2}\.\d{4}", numero)
        if not match:
            continue
        item["_tamanho_conteudo"] = len(str(item.get("texto_original") or item.get("tese_resumo") or ""))
        chave = (normalizar(item.get("tribunal")), match.group(0))
        grupos.setdefault(chave, []).append(item)
    return [sorted(grupo, key=lambda i: (-i["_tamanho_conteudo"], i["id"])) for grupo in grupos.values() if len(grupo) > 1]


def excluir_decisoes(decisao_ids: List[int], ator: Optional[str] = None) -> int:
    ids = sorted({int(decisao_id) for decisao_id in decisao_ids})
    if not ids:
        return 0
    placeholders = ", ".join("?" for _ in ids)
    with get_connection() as conn:
        cursor = conn.execute(f"DELETE FROM decisoes WHERE id IN ({placeholders})", ids)
        if cursor.rowcount:
            _registrar_evento_conn(conn, ator, "excluir_em_lote", "decisoes", detalhes={"ids": ids, "removidas": cursor.rowcount})
        return cursor.rowcount


def resetar_sequencia_banco(ator: Optional[str] = None) -> None:
    """Limpa as decisões e reseta o autoincremento para reiniciar do 1."""
    with get_connection() as conn:
        cursor = conn.cursor()
        quantidade = cursor.execute("SELECT COUNT(*) FROM decisoes").fetchone()[0]
        cursor.execute("DELETE FROM decisoes")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='decisoes'")
        _registrar_evento_conn(conn, ator, "resetar_base_demo", "decisoes", detalhes={"removidas": quantidade})
        conn.commit()


def obter_responsavel_atual() -> Optional[Dict[str, Any]]:
    """Retorna o registro mais recente do responsável do mês."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM responsavel_mes ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None


def verificar_status_responsavel() -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verifica se o responsável cadastrado está com autorização válida para hoje.
    Retorna (esta_valido, mensagem, dados_responsavel).
    """
    resp = obter_responsavel_atual()
    hoje = date.today().strftime("%Y-%m-%d")

    if not resp or not resp.get("ativo"):
        return False, "Nenhum responsável do mês cadastrado no momento.", None

    data_inicio = resp["data_inicio"]
    data_fim = resp["data_fim"]

    if data_inicio <= hoje <= data_fim:
        data_fim_fmt = datetime.strptime(data_fim, "%Y-%m-%d").strftime("%d/%m/%Y")
        return True, f"Autorizado até {data_fim_fmt}", resp
    elif hoje > data_fim:
        data_fim_fmt = datetime.strptime(data_fim, "%Y-%m-%d").strftime("%d/%m/%Y")
        return False, f"Acesso expirado em {data_fim_fmt}! Ciclo mensal encerrado.", resp
    else:
        data_ini_fmt = datetime.strptime(data_inicio, "%Y-%m-%d").strftime("%d/%m/%Y")
        return False, f"Acesso ainda não iniciado (vigência a partir de {data_ini_fmt}).", resp


def salvar_responsavel_mes(email: str, senha: str, data_inicio: str, data_fim: str, ator: Optional[str] = None) -> int:
    """Cadastra ou renova o responsável do ciclo mensal."""
    if not senha or not senha.strip():
        raise ValueError("A senha do responsável não pode ficar vazia.")
    with get_connection() as conn:
        cursor = conn.cursor()
        # Desativa anteriores
        cursor.execute("UPDATE responsavel_mes SET ativo = 0")
        cursor.execute(
            """
            INSERT INTO responsavel_mes (email, senha, data_inicio, data_fim, ativo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (email.strip().lower(), senha.strip(), data_inicio, data_fim),
        )
        _registrar_evento_conn(conn, ator, "atualizar_responsavel", "responsavel_mes", cursor.lastrowid)
        conn.commit()
        return cursor.lastrowid or 0


def atualizar_senha_responsavel(responsavel_id: int, senha_hash: str, ator: Optional[str] = None) -> bool:
    """Atualiza somente o hash da senha para migração segura de registros antigos."""
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE responsavel_mes SET senha = ? WHERE id = ?",
            (senha_hash, responsavel_id),
        )
        if cursor.rowcount:
            _registrar_evento_conn(conn, ator, "migrar_senha_responsavel", "responsavel_mes", responsavel_id)
        return cursor.rowcount > 0


def inserir_decisao(
    dados: DecisionData,
    usuario: Optional[str] = None,
    origem: Optional[str] = None,
) -> int:
    """Insere um novo registro de jurisprudência no banco com verificação de duplicidade."""
    hash_decisao = dados.get("hash") or calcular_hash_decisao(dados)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM decisoes WHERE hash = ?", (hash_decisao,))
        row_existente = cursor.fetchone()
        if row_existente:
            registrar_evento_auditoria(
                ator=usuario,
                acao="insercao_duplicada",
                recurso="decisoes",
                recurso_id=str(row_existente["id"]),
                detalhes={"hash": hash_decisao, "origem": origem},
            )
            return 0

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
            "texto_original": dados.get("texto_original"),
            "hash": hash_decisao,
            "usuario_importacao": usuario or dados.get("usuario_importacao"),
            "origem_boletim": origem or dados.get("origem_boletim"),
        }

        cursor.execute(
            """
            INSERT INTO decisoes (
                tribunal, tipo, identificador, titulo, ramo, status,
                em_alerta, prazo_alerta, data_limite_verificacao, relator,
                orgao_julgador, processo_origem, data_evento, tese_resumo,
                conclusao_comentarios, link_oficial, texto_original,
                hash, usuario_importacao, origem_boletim
            ) VALUES (
                :tribunal, :tipo, :identificador, :titulo, :ramo, :status,
                :em_alerta, :prazo_alerta, :data_limite_verificacao, :relator,
                :orgao_julgador, :processo_origem, :data_evento, :tese_resumo,
                :conclusao_comentarios, :link_oficial, :texto_original,
                :hash, :usuario_importacao, :origem_boletim
            )
            """,
            dados_completos,
        )
        novo_id = cursor.lastrowid or 0
        _registrar_evento_conn(conn, usuario, "insercao_decisao", "decisoes", novo_id,
                               {"hash": hash_decisao, "origem": origem})
        return novo_id


def excluir_decisao(decisao_id: int, ator: Optional[str] = None) -> bool:
    """Exclui uma decisão do banco pelo ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM decisoes WHERE id = ?", (decisao_id,))
        if cursor.rowcount:
            _registrar_evento_conn(conn, ator, "excluir", "decisao", decisao_id)
        return cursor.rowcount > 0


def atualizar_verificacao(
    decisao_id: int,
    nova_data_limite: Optional[str] = None,
    novo_status: Optional[str] = None,
    remover_alerta: bool = False,
    ator: Optional[str] = None,
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
        if cursor.rowcount:
            _registrar_evento_conn(conn, ator, "atualizar_verificacao", "decisao", decisao_id,
                                   {"remover_alerta": remover_alerta})
        return cursor.rowcount > 0


def listar_decisoes(
    tribunal: Optional[str] = None,
    ramo: Optional[str] = None,
    somente_alertas: bool = False,
    busca: Optional[str] = None,
    ordem: str = "recentes",
) -> List[Dict[str, Any]]:
    """
    Consulta as decisões cadastradas com filtros opcionais.
    - ordem='recentes': mais recentemente cadastradas primeiro (id DESC).
    - ordem='antigos': ordem original de cadastro (id ASC).
    - ordem='alerta_prazo': prazos mais próximos de vencer primeiro (data_limite_verificacao ASC).
    """
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

    if ordem == "alerta_prazo":
        query += """ ORDER BY
            CASE WHEN data_limite_verificacao IS NULL OR data_limite_verificacao = '' THEN 1 ELSE 0 END ASC,
            data_limite_verificacao ASC,
            id DESC"""
    elif ordem == "antigos":
        query += " ORDER BY id ASC"
    else:
        # Padrão: mais recentes cadastradas primeiro
        query += " ORDER BY id DESC"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
