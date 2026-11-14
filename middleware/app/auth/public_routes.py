# Rotas que NÃO exigem token. Tudo que não estiver aqui exige JWT válido.
# Lista explícita (allowlist): uma rota nova nasce protegida por padrão.
PUBLIC_PATHS = {
    "/health",
    "/auth/login",
    # Documentação interativa do FastAPI (útil em desenvolvimento/demo).
    "/docs",
    "/redoc",
    "/openapi.json",
}


def is_public(path: str) -> bool:
    """Compara o caminho exato (sem barra final), sem aceitar prefixos."""
    normalized = path.rstrip("/") or "/"
    return normalized in PUBLIC_PATHS   