"""Script de Benchmark e Comparação para Validação de Extração (Teste de Fogo).

Compara a triagem manual feita por um humano (ex.: colega do escritório)
com a extração e classificação automática produzida pelo sistema.

Uso:
    python scripts/avaliar_precisao_extracao.py --pdf caminho/boletim.pdf --processos_humano "proc1,proc2,proc3"
    ou modo interativo.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Set

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extractor import extrair_decisoes_de_texto, extrair_texto_pdf


def normalizar_cnj(texto: str) -> str:
    """Extrai apenas os números do padrão CNJ para comparação exata."""
    match = re.search(r"\d{7}-\d{2}\.\d{4}\.4\.\d{2}\.\d{4}", texto)
    if match:
        return re.sub(r"\D", "", match.group(0))
    # Caso não seja CNJ padrão, limpa pontuação básica
    return re.sub(r"\W", "", texto).lower()


def comparar_selecoes(
    processos_humano: List[str],
    decisoes_sistema: List[dict],
) -> dict:
    """Calcula métricas de precisão, revocação e lista as divergências."""
    set_humano: Set[str] = {normalizar_cnj(p) for p in processos_humano if normalizar_cnj(p)}
    
    mapa_sistema = {}
    for d in decisoes_sistema:
        identificador = d.get("processo_origem") or d.get("identificador") or ""
        cnj_norm = normalizar_cnj(identificador)
        if cnj_norm:
            mapa_sistema[cnj_norm] = d

    set_sistema = set(mapa_sistema.keys())

    em_comum = set_humano.intersection(set_sistema)
    apenas_humano = set_humano - set_sistema  # Falsos negativos: colega pegou, sistema perdeu
    apenas_sistema = set_sistema - set_humano  # Decisões adicionais que o sistema capturou

    total_humano = len(set_humano)
    total_sistema = len(set_sistema)

    cobertura = (len(em_comum) / total_humano * 100) if total_humano > 0 else 0.0
    precisao = (len(em_comum) / total_sistema * 100) if total_sistema > 0 else 0.0

    return {
        "total_humano": total_humano,
        "total_sistema": total_sistema,
        "em_comum": len(em_comum),
        "cobertura_percentual": cobertura,
        "precisao_percentual": precisao,
        "itens_em_comum": list(em_comum),
        "falsos_negativos": list(apenas_humano),
        "falsos_positivos": list(apenas_sistema),
    }


def imprimir_relatorio(resultado: dict):
    print("\n" + "=" * 65)
    print("📊 RELATÓRIO DO TESTE DE FOGO: HUMANO vs SISTEMA AUTOMÁTICO")
    print("=" * 65)
    print(f"Decisões selecionadas pela Colega (Humano): {resultado['total_humano']}")
    print(f"Decisões extraídas pelo Sistema:            {resultado['total_sistema']}")
    print(f"Decisões em comum (Concordância Total):     {resultado['em_comum']}")
    print(f"Taxa de Cobertura / Recall:                 {resultado['cobertura_percentual']:.1f}%")
    print(f"Taxa de Precisão:                           {resultado['precisao_percentual']:.1f}%")
    print("-" * 65)

    if resultado["falsos_negativos"]:
        print(f"\n⚠️ FALSOS NEGATIVOS ({len(resultado['falsos_negativos'])} decisões que a colega pegou e o sistema NÃO capturou):")
        for item in resultado["falsos_negativos"]:
            print(f"   • {item}")
        print("   -> Diagnóstico: ajustar regex de segmentação ou palavras-chave do filtro temático.")
    else:
        print("\n🎉 NENHUM falso negativo! Todas as decisões da colega foram capturadas pelo sistema!")

    if resultado["falsos_positivos"]:
        print(f"\nℹ️ DECISÕES ADICIONAIS ({len(resultado['falsos_positivos'])} que o sistema selecionou e a colega descartou):")
        for item in resultado["falsos_positivos"]:
            print(f"   • {item}")
        print("   -> Diagnóstico: conferir se são decisões válidas ou se o filtro precisa ser mais estrito.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compara seleção manual com a automática.")
    parser.add_argument("--pdf", help="Caminho do arquivo PDF do boletim")
    parser.add_argument("--processos", help="Lista de números de processo separados por vírgula")
    args = parser.parse_args()

    if args.pdf and args.processos:
        pdf_bytes = Path(args.pdf).read_bytes()
        texto = extrair_texto_pdf(pdf_bytes)
        candidatos = extrair_decisoes_de_texto(texto, apenas_adm_militar=True)
        processos_humano = [p.strip() for p in args.processos.split(",")]
        res = comparar_selecoes(processos_humano, candidatos)
        imprimir_relatorio(res)
    else:
        print("Módulo pronto para receber a seleção da colega na sexta-feira.")
