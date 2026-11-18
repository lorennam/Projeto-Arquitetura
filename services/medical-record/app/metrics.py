from prometheus_client import Counter, Histogram

ROTA_DESCONHECIDA = "nao_mapeada"

http_requests_total = Counter(
    "http_requests_total",
    "Total de requisições HTTP recebidas",
    ["service", "method", "route", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Duração das requisições HTTP em segundos",
    ["service", "method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

http_errors_total = Counter(
    "http_errors_total",
    "Total de respostas HTTP 5xx",
    ["service", "method", "route", "status"],
)


def rota_modelo(scope: dict) -> str:
    """Retorna o modelo da rota (/consultas/{consulta_id}), nunca o caminho real.

    Usar o caminho real criaria uma série nova por UUID. Rotas que não
    casaram com nenhuma definição (404) caem em um valor fixo, pelo mesmo motivo.
    """
    rota = scope.get("route")
    return getattr(rota, "path", None) or ROTA_DESCONHECIDA


def registrar_requisicao(
    service: str, method: str, route: str, status: int, duration_seconds: float
) -> None:
    status_label = str(status)
    http_requests_total.labels(service, method, route, status_label).inc()
    http_request_duration_seconds.labels(service, method, route).observe(duration_seconds)
    if status >= 500:
        http_errors_total.labels(service, method, route, status_label).inc()