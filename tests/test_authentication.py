from services.authentication import (
    autenticar_administrador,
    autenticar_responsavel,
    hash_senha,
    senha_precisa_migracao,
)


def test_login_administrativo_usa_credenciais_configuradas():
    assert autenticar_administrador("ADMIN@example.org", "senha-segura", "admin@example.org", "senha-segura")
    assert not autenticar_administrador("admin@example.org", "incorreta", "admin@example.org", "senha-segura")
    assert not autenticar_administrador("admin@example.org", "senha-segura", "", "")


def test_login_responsavel_normaliza_email_e_aceita_senha_unicode():
    responsavel = {"email": "fabio@example.org", "senha": "segurança"}

    assert autenticar_responsavel("FABIO@example.org", "segurança", responsavel)
    assert not autenticar_responsavel("outra@example.org", "segurança", responsavel)


def test_novas_senhas_sao_hashes_e_login_legado_pode_migrar():
    senha_hash = hash_senha("senha-com-acento")
    responsavel = {"email": "fabio@example.org", "senha": senha_hash}

    assert senha_hash != "senha-com-acento"
    assert autenticar_responsavel("fabio@example.org", "senha-com-acento", responsavel)
    assert not autenticar_responsavel("fabio@example.org", "errada", responsavel)
    assert not senha_precisa_migracao(senha_hash)
    assert senha_precisa_migracao("senha antiga em texto")
