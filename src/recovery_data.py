"""Carga pública inicial com registros recuperados e conferidos em fontes oficiais.

O marcador fica ao lado do SQLite, em diretório ignorado pelo Git. Assim a carga
acontece uma vez em uma instalação vazia, não reaparece se alguém excluir todos
os registros pelo app e se repete automaticamente quando o armazenamento efêmero
da hospedagem é recriado.
"""

from pathlib import Path
import sqlite3
from threading import Lock

from database import DB_PATH, get_connection, init_db, inserir_decisao


REGISTROS_PUBLICOS_RECUPERADOS = [
    {
        "tribunal": "STF",
        "tipo": "Tema de Repercussão Geral",
        "identificador": "Tema 1.460",
        "titulo": "Incorporação da GEAC aos proventos de professores da Bahia",
        "ramo": "Direito Administrativo / Servidor Público",
        "status": "Sem repercussão geral; trânsito em julgado",
        "em_alerta": 0,
        "prazo_alerta": "Concluído",
        "relator": "Ministro Presidente",
        "orgao_julgador": "Tribunal Pleno",
        "processo_origem": "RE 1.543.505, RE 1.543.482 e RE 1.543.701",
        "data_evento": "20/08/2026",
        "tese_resumo": (
            "É infraconstitucional e fática a controvérsia sobre a implantação da "
            "Gratificação por Estímulo à Atividade de Classe (GEAC) nos proventos "
            "de professores do Estado da Bahia aposentados antes da EC 41/2003."
        ),
        "link_oficial": "https://portal.stf.jus.br/jurisprudenciaRepercussao/verAndamentoProcesso.asp?classeProcesso=RE&incidente=7206065&numeroProcesso=1543505&numeroTema=1460",
        "origem_boletim": "Recuperação da carga anterior; conferido em fonte oficial",
    },
    {
        "tribunal": "STF",
        "tipo": "Tema de Repercussão Geral",
        "identificador": "Tema 1.478",
        "titulo": "Reajuste de vencimentos de servidores da educação básica de Minas Gerais",
        "ramo": "Direito Administrativo / Servidor Público",
        "status": "Sem repercussão geral; trânsito em julgado",
        "em_alerta": 0,
        "prazo_alerta": "Concluído",
        "relator": "Ministro Presidente",
        "orgao_julgador": "Tribunal Pleno",
        "processo_origem": "RE 1.576.462/MG",
        "data_evento": "04/11/2026",
        "tese_resumo": (
            "É infraconstitucional, aplicando-se os efeitos da ausência de "
            "repercussão geral, a controvérsia sobre a implementação do reajuste "
            "de 11,36% previsto para servidores do Grupo de Atividades de Educação "
            "Básica de Minas Gerais pela Lei estadual 22.062/2016."
        ),
        "link_oficial": "https://portal.stf.jus.br/jurisprudenciaRepercussao/verAndamentoProcesso.asp?classeProcesso=RE&incidente=7414025&numeroProcesso=1576462&numeroTema=1478",
        "origem_boletim": "Recuperação da carga anterior; conferido em fonte oficial",
    },
    {
        "tribunal": "STF",
        "tipo": "Tema de Repercussão Geral",
        "identificador": "Tema 1.308",
        "titulo": "Piso salarial nacional do magistério para servidores temporários",
        "ramo": "Direito Administrativo / Servidor Público",
        "status": "Julgado; embargos com modulação dos efeitos",
        "em_alerta": 0,
        "prazo_alerta": "Acompanhar aplicação da modulação",
        "relator": "Ministro Alexandre de Moraes",
        "orgao_julgador": "Tribunal Pleno",
        "processo_origem": "ARE 1.487.739/PE",
        "data_evento": "26/10/2026",
        "tese_resumo": (
            "O piso nacional da Lei 11.738/2008 aplica-se aos profissionais do "
            "magistério público da educação básica independentemente da natureza "
            "do vínculo, observados o Tema 551/STF e a ADI 6.196. O STF também "
            "fixou limite de 5% para cessão de professores efetivos a outros órgãos. "
            "Em embargos julgados em outubro de 2026, modulou os efeitos temporais."
        ),
        "link_oficial": "https://portal.stf.jus.br/jurisprudenciaRepercussao/verAndamentoProcesso.asp?classeProcesso=ARE&incidente=6894639&numeroProcesso=1487739&numeroTema=1308",
        "origem_boletim": "Recuperação da carga anterior; conferido em fonte oficial",
    },
    {
        "tribunal": "STF",
        "tipo": "Tema de Repercussão Geral",
        "identificador": "Tema 1.164",
        "titulo": "Extinção de cargos por limite da LRF e nomeação em concurso",
        "ramo": "Direito Administrativo / Concurso Público",
        "status": "Transitado em julgado",
        "em_alerta": 0,
        "prazo_alerta": "Concluído",
        "relator": "Ministro Flávio Dino",
        "orgao_julgador": "Tribunal Pleno",
        "processo_origem": "RE 1.316.010/PA",
        "data_evento": "26/03/2026",
        "tese_resumo": (
            "A extinção superveniente de cargos oferecidos em concurso, por superação "
            "do limite prudencial de gastos com pessoal, quando anterior ao fim da "
            "validade do certame e devidamente motivada, justifica mitigar o direito "
            "à nomeação de candidato aprovado dentro das vagas."
        ),
        "link_oficial": "https://portal.stf.jus.br/jurisprudenciaRepercussao/verAndamentoProcesso.asp?classeProcesso=RE&incidente=6128716&numeroProcesso=1316010&numeroTema=1164",
        "origem_boletim": "Recuperação da carga anterior; tese corrigida conforme fonte oficial",
    },
    {
        "tribunal": "STF",
        "tipo": "Tema de Repercussão Geral",
        "identificador": "Tema 1.167",
        "titulo": "Teto remuneratório no cálculo de pensão por morte de servidor",
        "ramo": "Direito Administrativo / Servidor Público",
        "status": "Julgado; trânsito em julgado",
        "em_alerta": 0,
        "prazo_alerta": "Concluído",
        "relator": "Ministro Flávio Dino",
        "orgao_julgador": "Tribunal Pleno",
        "processo_origem": "ARE 1.314.490/SP",
        "data_evento": "03/03/2026",
        "tese_resumo": (
            "Para o cálculo da pensão por morte do art. 40, § 7º, da Constituição, "
            "consideram-se apenas as parcelas efetivamente percebidas pelo servidor, "
            "excluídos valores acima do teto ou subteto remuneratório, sobre os quais "
            "não incidiu contribuição previdenciária."
        ),
        "link_oficial": "https://portal.stf.jus.br/jurisprudenciaRepercussao/verAndamentoProcesso.asp?classeProcesso=ARE&incidente=6122934&numeroProcesso=1314490&numeroTema=1167",
        "origem_boletim": "Recuperação da carga anterior; tese conferida em fonte oficial",
    },
    {
        "tribunal": "STF",
        "tipo": "Tema de Repercussão Geral",
        "identificador": "Tema 1.388",
        "titulo": "Estado civil e vínculos familiares no ingresso e permanência em formação militar",
        "ramo": "Direito Militar / Administrativo",
        "status": "Transitado em julgado",
        "em_alerta": 0,
        "prazo_alerta": "Concluído",
        "relator": "Ministro Luiz Fux",
        "orgao_julgador": "Tribunal Pleno",
        "processo_origem": "RE 1.530.083/RN",
        "data_evento": "05/03/2026",
        "tese_resumo": (
            "É inconstitucional condicionar o ingresso e a permanência em órgãos de "
            "formação ou graduação militar à inexistência de vínculo conjugal, união "
            "estável, maternidade, paternidade ou dependência socioafetiva."
        ),
        "link_oficial": "https://portal.stf.jus.br/jurisprudenciaRepercussao/verAndamentoProcesso.asp?classeProcesso=RE&incidente=7120334&numeroProcesso=1530083&numeroTema=1388",
        "origem_boletim": "Recuperação da carga anterior; conferido em fonte oficial",
    },
    {
        "tribunal": "STJ",
        "tipo": "Recurso Repetitivo",
        "identificador": "Tema 1.444",
        "titulo": "Expedição de precatório ou RPV com restrição de saque antes do trânsito em julgado",
        "ramo": "Direito Administrativo / Processual Civil",
        "status": "Afetado ao rito dos repetitivos; pendente de julgamento",
        "em_alerta": 1,
        "prazo_alerta": "Acompanhar julgamento",
        "relator": "Ministro Teodoro Silva Santos",
        "orgao_julgador": "Primeira Seção",
        "processo_origem": "ProAfR no REsp 2.250.310/AL e REsp 2.250.079/AL",
        "data_evento": "03/06/2026",
        "tese_resumo": (
            "Controvérsia afetada: definir se é possível expedir precatório ou RPV, "
            "com ordem de restrição ao saque, antes do trânsito em julgado do "
            "cumprimento de sentença. Ainda não é tese julgada."
        ),
        "link_oficial": "https://processo.stj.jus.br/jurisprudencia/externo/informativo/?livre=@CNOT=022378",
        "origem_boletim": "Recuperação da carga anterior; afetação conferida em fonte oficial",
    },
    {
        "tribunal": "STJ",
        "tipo": "Recurso Repetitivo",
        "identificador": "Tema 1.300",
        "titulo": "Ônus da prova sobre lançamentos a débito nas contas individualizadas do PASEP",
        "ramo": "Direito Administrativo / Servidor Público",
        "status": "Transitado em julgado",
        "em_alerta": 0,
        "prazo_alerta": "Concluído",
        "relator": "Ministra Maria Thereza de Assis Moura",
        "orgao_julgador": "Primeira Seção",
        "processo_origem": "REsp 2.162.222/PE e correlatos",
        "data_evento": "18/09/2025",
        "tese_resumo": (
            "Nas ações sobre saques em conta individual do PASEP, cabe ao participante "
            "provar os saques por crédito em conta ou PASEP-FOPAG; cabe ao réu provar "
            "os saques em caixa de agência do Banco do Brasil."
        ),
        "link_oficial": "https://scon.stj.jus.br/SCON/jurisprudencia/toc.jsp?O=JT&b=ACOR&livre=202402922923.REG.+E+18%2F09%2F2025.FONT.",
        "origem_boletim": "Recuperação da carga anterior; tese conferida em fonte oficial",
    },
    {
        "tribunal": "TNU",
        "tipo": "Tema Representativo da Controvérsia",
        "identificador": "Tema 391",
        "titulo": "Bônus de Eficiência na base de cálculo de férias e gratificação natalina",
        "ramo": "Direito Administrativo / Servidor Público",
        "status": "Julgado; acórdão publicado",
        "em_alerta": 0,
        "prazo_alerta": "Concluído",
        "relator": "Juiz Federal Fábio de Souza Silva; relatora para acórdão Marina Vasques Duarte",
        "orgao_julgador": "Turma Nacional de Uniformização",
        "processo_origem": "PEDILEF 5061419-84.2024.4.04.7100/RS",
        "data_evento": "28/09/2026",
        "tese_resumo": (
            "O Bônus de Eficiência e Produtividade pago até março de 2024 aos "
            "auditores-fiscais e analistas tributários da ativa integra a remuneração "
            "e compõe a base de cálculo da gratificação natalina e do adicional de férias."
        ),
        "link_oficial": "https://www.cjf.jus.br/cjf/corregedoria-da-justica-federal/turma-nacional-de-uniformizacao/temas-representativos/tema-391",
        "origem_boletim": "Recuperação da carga anterior; tese conferida em fonte oficial",
    },
]

_CARGA_LOCK = Lock()


def _marker_path() -> Path:
    return DB_PATH.parent / ".carga-publica-recuperada-v1"


def carregar_recuperacao_publica() -> int:
    """Carrega os registros verificados uma única vez em um SQLite vazio.

    Bases existentes nunca são alteradas. O marcador impede que a exclusão
    deliberada de todos os registros faça a carga reaparecer em um rerun.
    """
    init_db()
    with _CARGA_LOCK:
        marker = _marker_path()
        if marker.exists():
            return 0

        with get_connection() as conn:
            quantidade = conn.execute("SELECT COUNT(*) FROM decisoes").fetchone()[0]

        if quantidade:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("Base já tinha dados; carga inicial ignorada.\n", encoding="utf-8")
            return 0

        inseridos = 0
        for registro in REGISTROS_PUBLICOS_RECUPERADOS:
            try:
                novo_id = inserir_decisao(
                    registro,
                    usuario="carga-publica-inicial",
                    origem=registro["origem_boletim"],
                )
            except sqlite3.IntegrityError:
                # Sessões concorrentes usam o índice único de hash do banco;
                # a segunda trata o registro já criado como concluído.
                novo_id = 0
                with get_connection() as conn:
                    hash_registro = conn.execute(
                        "SELECT hash FROM decisoes WHERE tribunal = ? AND identificador = ?",
                        (registro["tribunal"], registro["identificador"]),
                    ).fetchone()
                if hash_registro is None:
                    raise
            inseridos += int(bool(novo_id))

        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            f"Carga pública v1 verificada; {len(REGISTROS_PUBLICOS_RECUPERADOS)} registros.\n",
            encoding="utf-8",
        )
        return inseridos
