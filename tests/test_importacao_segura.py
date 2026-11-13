from io import BytesIO

import pytest

from modules.importacao import baixar_pdf_oficial, validar_pdf_enviado


class Resposta:
    def __init__(self, status=200, headers=None, partes=(), url="https://www.trf1.jus.br/arquivo.pdf"):
        self.status_code = status
        self.headers = headers or {}
        self._partes = partes
        self.url = url
        self.closed = False

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307, 308)

    @property
    def is_permanent_redirect(self):
        return self.status_code in (301, 308)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def iter_content(self, chunk_size):
        yield from self._partes


class SessaoFalsa:
    def __init__(self, respostas):
        self.respostas = iter(respostas)
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append((url, kwargs))
        return next(self.respostas)


def test_redirecionamento_nao_oficial_e_bloqueado_antes_do_segundo_get():
    sessao = SessaoFalsa([Resposta(302, {"Location": "https://example.com/arquivo.pdf"})])
    with pytest.raises(ValueError, match="não oficial"):
        baixar_pdf_oficial("https://www.trf1.jus.br/arquivo.pdf", sessao=sessao)
    assert len(sessao.urls) == 1
    assert sessao.urls[0][1]["allow_redirects"] is False
    assert sessao.urls[0][1]["stream"] is True


def test_download_le_em_stream_e_rejeita_conteudo_acima_do_limite(monkeypatch):
    import modules.importacao as importacao

    monkeypatch.setattr(importacao, "MAX_PDF_BYTES", 5)
    sessao = SessaoFalsa([Resposta(partes=[b"%PDF-", b"123456"])])
    with pytest.raises(ValueError, match="20 MB"):
        baixar_pdf_oficial("https://www.trf1.jus.br/arquivo.pdf", sessao=sessao)


def test_pdf_enviado_verifica_tamanho_e_assinatura():
    class Upload(BytesIO):
        size = 10

    assert validar_pdf_enviado(Upload(b"%PDF-1.7\ntexto")) == b"%PDF-1.7\ntexto"
    with pytest.raises(ValueError, match="assinatura"):
        validar_pdf_enviado(Upload(b"conteudo falso"))

    class Grande:
        size = 20 * 1024 * 1024 + 1

        def read(self, _size):
            raise AssertionError("o arquivo excedente não deve ser lido")

    with pytest.raises(ValueError, match="20 MB"):
        validar_pdf_enviado(Grande())
