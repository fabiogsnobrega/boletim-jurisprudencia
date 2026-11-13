"""Classificação temática determinística ou por modelo local treinado."""

import pickle
from pathlib import Path
from typing import Any, Dict, Tuple


CAMINHO_MODELO_ML = Path(__file__).resolve().parents[3] / "data" / "modelo_classificador_ml.pkl"

PESOS_TEMATICOS = {
    "Direito Militar": [
        "militar", "militares", "forças armadas", "exército", "marinha", "aeronáutica",
        "caserna", "soldado", "sargento", "oficial", "estatuto dos militares",
        "pensão militar", "licença especial", "ex-combatente", "ambiente castrense"
    ],
    "Direito Administrativo / Servidor Público": [
        "servidor público", "servidora pública", "servidores públicos", "remuneração",
        "vencimentos", "piso salarial", "magistério", "professores", "paridade",
        "aposentadoria por invalidez", "reversão", "lei 8.112", "progressão funcional",
        "bônus de eficiência", "bepata", "perito médico", "gratificação", "geac",
        "reajuste de 28,86%", "pasep"
    ],
    "Direito Administrativo / Concurso Público": [
        "concurso público", "candidato", "candidata", "edital", "vagas imediatas",
        "cadastro de reserva", "lista de espera", "investigação social", "vida pregressa",
        "eliminação de candidato", "direito subjetivo à nomeação"
    ],
    "Direito Administrativo / Processual e Precatórios": [
        "precatório", "precatórios", "rpv", "requisição de pequeno valor", "bloqueio de saque",
        "cumprimento de sentença", "fazenda pública", "habilitação de herdeiros",
        "prescrição quinquenal", "fundo de direito"
    ],
    "Direito Administrativo / Responsabilidade Civil": [
        "responsabilidade civil", "dano moral", "indenização", "nexo causal",
        "ato ilícito", "ofensa verbal"
    ],
}


class ClassificadorJurisprudenciaML:
    """Prediz o ramo do direito usando modelo local ou pesos temáticos."""

    def __init__(self) -> None:
        self.modelo = None
        self.carregar_modelo()

    def carregar_modelo(self) -> bool:
        """Carrega o modelo salvo, se existir e puder ser lido."""
        if CAMINHO_MODELO_ML.exists():
            try:
                with open(CAMINHO_MODELO_ML, "rb") as arquivo:
                    self.modelo = pickle.load(arquivo)
                return True
            except Exception:
                self.modelo = None
        return False

    def salvar_modelo(self, modelo_treinado: Any) -> None:
        """Salva o modelo treinado no diretório de dados do projeto."""
        CAMINHO_MODELO_ML.parent.mkdir(parents=True, exist_ok=True)
        with open(CAMINHO_MODELO_ML, "wb") as arquivo:
            pickle.dump(modelo_treinado, arquivo)
        self.modelo = modelo_treinado

    def sugerir_relevancia(self, decisao: dict) -> str:
        """Gera uma frase explicativa de por que a decisão pode ser relevante.

        A sugestão utiliza o ramo previsto e a confiança do modelo/heurística.
        Se a decisão já possui ``ramo`` definido, ele será usado; caso contrário,
        o método ``predizer_ramo`` é chamado sobre o ``texto_original`` (ou
        ``tese_resumo`` como fallback).
        """
        # Determine texto de base para classificação
        texto = decisao.get("texto_original") or decisao.get("tese_resumo") or ""
        if not texto:
            return "Sem texto suficiente para avaliação de relevância."

        # Prediz ramo
        ramo, _ = self.predizer_ramo(texto)
        # Mensagem direta sem jargão estatístico
        return f"Matéria identificada: **{ramo}**"

    def predizer_ramo(self, texto: str) -> Tuple[str, float]:
        """Retorna o ramo previsto e uma pontuação heurística de confiança."""
        if self.modelo is not None and hasattr(self.modelo, "predict"):
            try:
                ramo = self.modelo.predict([texto])[0]
                confianca = 0.95
                if hasattr(self.modelo, "predict_proba"):
                    confianca = float(max(self.modelo.predict_proba([texto])[0]))
                return str(ramo), confianca
            except Exception:
                pass

        texto_lower = texto.lower()
        pontuacoes = {
            ramo: sum(len(palavra.split()) * 2 for palavra in palavras if palavra in texto_lower)
            for ramo, palavras in PESOS_TEMATICOS.items()
        }
        ramo_top = max(pontuacoes, key=pontuacoes.get)
        score = pontuacoes[ramo_top]
        if score > 0:
            return ramo_top, min(score / 10.0, 1.0)
        return "Direito Administrativo Geral", 0.5


classificador_global = ClassificadorJurisprudenciaML()
