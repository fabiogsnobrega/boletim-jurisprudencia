"""Comparação de credenciais sem acoplamento à interface Streamlit."""

import hashlib
import hmac
import secrets


_ITERACOES_PBKDF2 = 310_000
_PREFIXO_HASH = "pbkdf2_sha256$"


def _comparar(a: str, b: str) -> bool:
    return hmac.compare_digest(str(a).encode("utf-8"), str(b).encode("utf-8"))


def autenticar_administrador(
    email: str,
    senha: str,
    email_configurado: str,
    senha_configurada: str,
) -> bool:
    """Compara credenciais configuradas sem manter segredos no código-fonte."""
    if not email_configurado or not senha_configurada:
        return False
    email_ok = _comparar(email.strip().casefold(), email_configurado.strip().casefold())
    senha_ok = _comparar(senha, senha_configurada)
    return email_ok and senha_ok


def autenticar_responsavel(email: str, senha: str, responsavel: dict) -> bool:
    """Confere o login vigente do responsável do mês."""
    if not responsavel:
        return False
    email_ok = _comparar(email.strip().casefold(), str(responsavel.get("email", "")).casefold())
    senha_armazenada = str(responsavel.get("senha", ""))
    senha_ok = verificar_senha(senha, senha_armazenada)
    return email_ok and senha_ok


def hash_senha(senha: str) -> str:
    """Gera hash PBKDF2 com salt aleatório para novas senhas do responsável."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt, _ITERACOES_PBKDF2
    )
    return f"{_PREFIXO_HASH}{_ITERACOES_PBKDF2}${salt.hex()}${digest.hex()}"


def verificar_senha(senha: str, armazenada: str) -> bool:
    """Aceita hashes novos e senha em texto legado para migração no login."""
    if not armazenada.startswith(_PREFIXO_HASH):
        return _comparar(senha, armazenada)
    try:
        _, iteracoes, salt_hex, digest_hex = armazenada.split("$", maxsplit=3)
        digest = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), bytes.fromhex(salt_hex), int(iteracoes)
        )
        return _comparar(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def senha_precisa_migracao(armazenada: str) -> bool:
    return not armazenada.startswith(_PREFIXO_HASH)
