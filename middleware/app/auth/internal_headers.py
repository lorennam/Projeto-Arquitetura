# Headers que o gateway usa para repassar a identidade já validada aos serviços.
# Só o gateway pode defini-los: qualquer valor vindo do cliente é descartado.
USER_ID_HEADER = "X-User-Id"
USER_ROLE_HEADER = "X-User-Role"

# Prefixo reservado para uso interno. Qualquer header X-User-* vindo de fora é removido.
INTERNAL_PREFIX = "x-user-"


def strip_internal_headers(headers: dict) -> dict:
    """Remove headers de identidade enviados pelo cliente (anti-spoofing)."""
    return {
        k: v
        for k, v in headers.items()
        if not k.lower().startswith(INTERNAL_PREFIX)
    }


def build_internal_headers(user: dict) -> dict:
    """Monta os headers de identidade a partir do usuário validado no JWT."""
    return {
        USER_ID_HEADER: user["username"],
        USER_ROLE_HEADER: user["role"],
    }