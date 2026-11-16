"""Observabilidade do serviço: logs JSON com correlation_id e métricas Prometheus."""
import logging
import os
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

import correlation
import metrics
from logging_json import configurar_logging

logger = logging.getLogger("http")

# Rotas de infraestrutura: não geram log nem métrica (o healthcheck e o scrape
# chamam a cada poucos segundos e poluiriam as duas saídas).
ROTAS_SEM_LOG = {"/health", "/metrics"}


def _registrar(
    request: Request, servico: str, status: int, inicio: float, com_excecao: bool = False
) -> None:
    if request.url.path in ROTAS_SEM_LOG:
        return
    duracao = time.perf_counter() - inicio
    metrics.registrar_requisicao(
        servico, request.method, metrics.rota_modelo(request.scope), status, duracao
    )
    nivel = logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO
    logger.log(
        nivel,
        "requisição concluída",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "duration_ms": round(duracao * 1000, 2),
        },
        exc_info=com_excecao,
    )


def configurar_observabilidade(app: FastAPI, servico: str) -> None:
    configurar_logging(servico, os.getenv("LOG_LEVEL", "INFO"))

    @app.get("/metrics", include_in_schema=False)
    def exportar_metricas() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.middleware("http")
    async def observabilidade(request: Request, call_next):
        cid = request.headers.get(correlation.HEADER) or correlation.gerar()
        token = correlation.definir(cid)
        inicio = time.perf_counter()
        try:
            resposta = await call_next(request)
        except Exception:
            _registrar(request, servico, 500, inicio, com_excecao=True)
            raise
        else:
            resposta.headers[correlation.HEADER] = cid
            _registrar(request, servico, resposta.status_code, inicio)
            return resposta
        finally:
            correlation.resetar(token)