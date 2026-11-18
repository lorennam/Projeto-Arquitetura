import json
import logging

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

import correlation
from main import app
from repository import repositorio

CONSULTA_ID = "3f2b8c1e-5d4a-4b6e-9a7c-1d2e3f4a5b6c"


class _Coletor(logging.Handler):
    """Guarda os registros do logger 'http' já passando pelo filtro de correlation_id."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.addFilter(correlation.CorrelationIdFilter())
        self.registros = []

    def emit(self, record):
        self.registros.append(record)


@pytest.fixture
def logs_http():
    logger = logging.getLogger("http")
    coletor = _Coletor()
    nivel_anterior = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(coletor)
    yield coletor.registros
    logger.removeHandler(coletor)
    logger.setLevel(nivel_anterior)


def _contagem(nome, **rotulos):
    rotulos = {"service": "scheduling", **rotulos}
    return REGISTRY.get_sample_value(nome, rotulos) or 0.0


# ---------- correlation_id ----------

def test_gera_correlation_id_quando_header_nao_vem(client):
    resposta = client.get("/consultas")
    assert resposta.headers[correlation.HEADER]


def test_reaproveita_correlation_id_recebido(client):
    resposta = client.get("/consultas", headers={correlation.HEADER: "abc-123"})
    assert resposta.headers[correlation.HEADER] == "abc-123"


def test_correlation_id_sai_tambem_em_erro(client):
    resposta = client.get(f"/consultas/{CONSULTA_ID}", headers={correlation.HEADER: "abc-404"})
    assert resposta.status_code == 404
    assert resposta.headers[correlation.HEADER] == "abc-404"


# ---------- logs ----------

def test_log_da_requisicao_tem_os_campos_esperados(client, logs_http):
    client.get("/consultas", headers={correlation.HEADER: "abc-123"})
    registro = logs_http[-1]
    assert registro.method == "GET"
    assert registro.path == "/consultas"
    assert registro.status == 200
    assert registro.duration_ms >= 0
    assert registro.correlation_id == "abc-123"


def test_nivel_do_log_acompanha_o_status(client, logs_http):
    client.get("/consultas")
    client.get(f"/consultas/{CONSULTA_ID}")
    assert [r.levelno for r in logs_http] == [logging.INFO, logging.WARNING]


def test_health_e_metrics_nao_geram_log(client, logs_http):
    client.get("/health")
    client.get("/metrics")
    assert logs_http == []


def test_formatter_emite_json_com_service_e_correlation_id():
    handlers = [
        h for h in logging.getLogger().handlers
        if not h.__class__.__module__.startswith("_pytest")
    ]
    assert handlers, "configurar_logging deveria instalar um handler no logger raiz"
    registro = logging.LogRecord("http", logging.INFO, __file__, 1, "requisição concluída", None, None)
    registro.method, registro.path, registro.status, registro.duration_ms = "GET", "/x", 200, 1.5
    token = correlation.definir("abc-json")
    try:
        handlers[0].filter(registro)
        linha = handlers[0].format(registro)
    finally:
        correlation.resetar(token)
    dados = json.loads(linha)
    for campo in ("timestamp", "level", "service", "message", "correlation_id",
                  "method", "path", "status", "duration_ms"):
        assert campo in dados
    assert dados["service"] == "scheduling"
    assert dados["correlation_id"] == "abc-json"


# ---------- /metrics ----------

def test_metrics_responde_em_formato_prometheus(client):
    client.get("/consultas")
    resposta = client.get("/metrics")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in resposta.text
    assert "http_request_duration_seconds_bucket" in resposta.text


def test_metrics_conta_requisicoes_por_rota_modelo(client):
    rotulos = dict(method="GET", route="/consultas/{consulta_id}", status="404")
    antes = _contagem("http_requests_total", **rotulos)
    client.get(f"/consultas/{CONSULTA_ID}")
    assert _contagem("http_requests_total", **rotulos) == antes + 1
    assert CONSULTA_ID not in client.get("/metrics").text


def test_metrics_agrupa_rotas_inexistentes(client):
    rotulos = dict(method="GET", route="nao_mapeada", status="404")
    antes = _contagem("http_requests_total", **rotulos)
    client.get("/rota-que-nao-existe")
    client.get("/outra-rota-que-nao-existe")
    assert _contagem("http_requests_total", **rotulos) == antes + 2
    assert "rota-que-nao-existe" not in client.get("/metrics").text


def test_health_e_metrics_ficam_fora_das_metricas(client):
    client.get("/health")
    client.get("/metrics")
    texto = client.get("/metrics").text
    assert 'route="/health"' not in texto
    assert 'route="/metrics"' not in texto


def test_erro_5xx_conta_em_http_errors_total(monkeypatch):
    def quebra():
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(repositorio, "listar", quebra)
    rotulos = dict(method="GET", route="/consultas", status="500")
    antes = _contagem("http_errors_total", **rotulos)

    cliente = TestClient(app, raise_server_exceptions=False)
    resposta = cliente.get("/consultas")

    assert resposta.status_code == 500
    assert _contagem("http_errors_total", **rotulos) == antes + 1
    assert _contagem("http_requests_total", **rotulos) >= 1


def test_erro_4xx_nao_conta_em_http_errors_total(client):
    rotulos = dict(method="GET", route="/consultas/{consulta_id}", status="404")
    antes = _contagem("http_errors_total", **rotulos)
    client.get(f"/consultas/{CONSULTA_ID}")
    assert _contagem("http_errors_total", **rotulos) == antes