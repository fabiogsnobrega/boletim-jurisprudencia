"""Dados fictícios usados apenas para apresentar a interface com uma base vazia."""

from datetime import date, timedelta


def criar_decisoes_demo() -> list[dict]:
    """Retorna exemplos não persistidos e explicitamente fictícios."""
    hoje = date.today()
    return [
        {
            "id": 990001,
            "tribunal": "TRF1",
            "tipo": "Exemplo de decisão",
            "identificador": "EXEMPLO-001",
            "titulo": "EXEMPLO FICTÍCIO · Concurso público e ordem de convocação",
            "ramo": "Direito Administrativo / Concurso Público",
            "status": "Demonstração",
            "em_alerta": 1,
            "prazo_alerta": "Exemplo de acompanhamento",
            "data_limite_verificacao": (hoje + timedelta(days=15)).isoformat(),
            "relator": "Não se aplica — conteúdo fictício",
            "orgao_julgador": "Exemplo demonstrativo",
            "processo_origem": "Sem processo real",
            "data_evento": hoje.strftime("%d/%m/%Y"),
            "tese_resumo": (
                "Conteúdo fictício para demonstrar a apresentação de uma tese sobre concurso público. "
                "Não corresponde a julgamento ou orientação jurídica real."
            ),
            "conclusao_comentarios": None,
            "link_oficial": None,
        },
        {
            "id": 990002,
            "tribunal": "TRF5",
            "tipo": "Exemplo de decisão",
            "identificador": "EXEMPLO-002",
            "titulo": "EXEMPLO FICTÍCIO · Carreira e desenvolvimento funcional",
            "ramo": "Direito Administrativo / Servidor Público",
            "status": "Demonstração",
            "em_alerta": 0,
            "prazo_alerta": "Concluído",
            "data_limite_verificacao": None,
            "relator": "Não se aplica — conteúdo fictício",
            "orgao_julgador": "Exemplo demonstrativo",
            "processo_origem": "Sem processo real",
            "data_evento": hoje.strftime("%d/%m/%Y"),
            "tese_resumo": (
                "Exemplo fictício de como o sistema organiza informações sobre carreira pública. "
                "Os fatos e a conclusão não representam decisão judicial."
            ),
            "conclusao_comentarios": None,
            "link_oficial": None,
        },
        {
            "id": 990003,
            "tribunal": "TNU",
            "tipo": "Exemplo de decisão",
            "identificador": "EXEMPLO-003",
            "titulo": "EXEMPLO FICTÍCIO · Benefício relacionado à carreira militar",
            "ramo": "Direito Militar",
            "status": "Demonstração",
            "em_alerta": 0,
            "prazo_alerta": "Concluído",
            "data_limite_verificacao": None,
            "relator": "Não se aplica — conteúdo fictício",
            "orgao_julgador": "Exemplo demonstrativo",
            "processo_origem": "Sem processo real",
            "data_evento": hoje.strftime("%d/%m/%Y"),
            "tese_resumo": (
                "Exemplo fictício para mostrar a classificação temática e os campos de uma decisão. "
                "Não deve ser citado nem utilizado como fundamento jurídico."
            ),
            "conclusao_comentarios": None,
            "link_oficial": None,
        },
    ]


def filtrar_decisoes_demo(
    decisoes: list[dict], tribunal: str = "Todos", ramo: str = "Todos", busca: str = ""
) -> list[dict]:
    """Aplica aos exemplos os filtros usados na consulta pública."""
    termo = (busca or "").strip().casefold()
    resultado = []
    for decisao in decisoes:
        if tribunal != "Todos" and decisao["tribunal"] != tribunal:
            continue
        if ramo != "Todos" and ramo.casefold() not in decisao["ramo"].casefold():
            continue
        texto = " ".join(str(valor or "") for valor in decisao.values()).casefold()
        if termo and termo not in texto:
            continue
        resultado.append(decisao)
    return resultado
