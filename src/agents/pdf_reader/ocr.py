"""Stub para OCR futuro.

Este módulo contém a assinatura da função que, quando implementada,
receberá uma imagem (por exemplo, o bitmap de uma página PDF) e devolverá
uma string com o texto reconhecido.

A ideia é chamar OCR **apenas** nas páginas onde a extração nativa
(`pypdf`) retornou texto vazio, evitando processamento desnecessário.

Por enquanto, a função devolve `None` e serve apenas como ponto de
extensão para o próximo sprint.
"""

from typing import Optional

def ocr_pagina(imagem_bytes: bytes) -> Optional[str]:
    """Reconhece texto em uma imagem de página.

    Parameters
    ----------
    imagem_bytes: bytes
        Dados da imagem (por exemplo, PNG ou JPEG) contendo a página do
        PDF a ser processada.

    Returns
    -------
    Optional[str]
        Texto reconhecido ou ``None`` caso ainda não haja implementação.
    """
    # TODO: integrar pytesseract ou outro motor OCR.
    return None
