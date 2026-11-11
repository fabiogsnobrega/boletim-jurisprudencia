"""Testes de integridade das dependências do requirements.txt."""

from pathlib import Path
import importlib
import pytest


def obter_pacotes_requirements():
    req_path = Path(__file__).resolve().parents[1] / "requirements.txt"
    pacotes = []
    mapeamento_modulos = {
        "beautifulsoup4": "bs4",
        "pypdf": "pypdf",
        "scikit-learn": "sklearn",
    }
    with open(req_path, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            nome_pacote = linha.split(">=")[0].split("==")[0].split("<=")[0].strip()
            modulo = mapeamento_modulos.get(nome_pacote, nome_pacote)
            pacotes.append(modulo)
    return pacotes


@pytest.mark.parametrize("modulo", obter_pacotes_requirements())
def test_importacao_dependencias(modulo):
    """Garante que todas as dependências declaradas podem ser importadas sem erro."""
    try:
        importlib.import_module(modulo)
    except ImportError as e:
        pytest.fail(f"Dependência obrigatória '{modulo}' não pôde ser importada: {e}")
