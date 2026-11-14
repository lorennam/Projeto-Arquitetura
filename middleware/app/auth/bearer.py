from typing import Optional


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extrai o token de um header 'Authorization: Bearer <token>'.

    Retorna None se o header estiver ausente, em outro formato
    ou com o token vazio.
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]