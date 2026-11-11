from datetime import datetime, timedelta, timezone

import jwt

from .config import JWT_ALGORITHM, JWT_EXPIRES_MINUTES, JWT_SECRET


def create_access_token(username: str, role: str) -> str:
    """Gera um JWT assinado com usuário (sub), papel (role) e expiração (exp)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRES_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Valida assinatura e expiração e retorna o payload.

    Levanta jwt.ExpiredSignatureError (token expirado) ou
    jwt.InvalidTokenError (assinatura inválida, token malformado, etc.).
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])