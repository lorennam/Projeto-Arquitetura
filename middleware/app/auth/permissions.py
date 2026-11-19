# Tabela de permissões: serviço -> papel -> métodos HTTP permitidos.
# Allowlist: o que não está listado é NEGADO (privilégio mínimo).
ALL_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

PERMISSIONS = {
    "scheduling": {
        "patient": {"GET", "POST"},
        "doctor": ALL_METHODS,
        "admin": ALL_METHODS,
    },
    "medical-record": {
        # Dado clínico sensível: apenas médico.
        "doctor": ALL_METHODS,
    },
    "notification": {
        "patient": {"GET"},
        "doctor": {"GET"},
        "admin": ALL_METHODS,
    },
    "patient-extra-point": {
        "patient": {"GET"},
        "admin": ALL_METHODS,
    },
}

def service_from_path(path: str):
    """Extrai o nome do serviço de um caminho '/api/<servico>/...'.

    Retorna None se o caminho não for de uma rota de serviço.
    """
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "api":
        return parts[1]
    return None


def is_allowed(role: str, service: str, method: str) -> bool:
    """True se o papel pode usar o método HTTP naquele serviço.

    Allowlist: serviço ou papel ausente da tabela => negado.
    """
    allowed_methods = PERMISSIONS.get(service, {}).get(role, set())
    return method.upper() in allowed_methods