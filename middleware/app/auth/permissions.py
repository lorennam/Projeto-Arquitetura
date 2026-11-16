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
}