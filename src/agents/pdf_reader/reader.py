"""Conversão de PDFs recebidos pelo sistema em texto, preservando a separação por página.

Este módulo oferece duas funções públicas:
- ``extrair_texto_pdf_por_pagina`` devolve uma lista de tuplas ``(num_pagina, texto, vazia)``.
- ``extrair_texto_pdf`` mantém a API original (retorna o texto concatenado) e continua sendo usado pelo resto da aplicação.

A separação por página facilita a posterior integração de OCR apenas nas páginas que não contêm texto extraível.
"""

import io
from typing import List, Tuple

from pypdf import PdfReader


def extrair_texto_pdf_por_pagina(arquivo_bytes: bytes) -> List[Tuple[int, str, bool]]:
    """Extrai o texto de cada página de um PDF.

    Returns
    -------
    List[Tuple[int, str, bool]]
        Cada item contém ``(numero_da_pagina, texto_extraido, pagina_vazia)``.
        ``pagina_vazia`` será ``True`` quando ``extract_text`` retorna ``None`` ou uma string vazia.
    """
    leitor = PdfReader(io.BytesIO(arquivo_bytes))
    resultado: List[Tuple[int, str, bool]] = []
    for idx, pagina in enumerate(leitor.pages, start=1):
        texto = pagina.extract_text() or ""
        vazia = len(texto.strip()) == 0
        resultado.append((idx, texto, vazia))
    return resultado


def extrair_texto_pdf(arquivo_bytes: bytes) -> str:
    """Mantém compatibilidade com a API anterior.

    Concatena o texto de todas as páginas, separando por duas quebras de linha.
    Páginas vazias são incluídas como strings vazias para preservar a ordem.
    """
    paginas = extrair_texto_pdf_por_pagina(arquivo_bytes)
    textos = [texto for _, texto, _ in paginas]
    return "\n\n".join(textos)

