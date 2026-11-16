"""Observabilidade do serviço: logs JSON com correlation_id (e, em seguida, métricas)."""
import logging
import os
import time

from fastapi import FastAPI, Request

import correlation
from logging_json import configurar_logging

logger = logging.getLogger("http")

# Rotas de infraestrutura: não geram log por requisição (o healthcheck chama a cada poucos segundos).
ROTAS_SEM_LOG = {"/health", "/metrics"}


def _registrar(request: Request, status: int, inicio: float, com_excecao: bool = False) -> None:
    if request.url.path in ROTAS_SEM_LOG:
        return
    nivel = logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO
    logger.log(
        nivel,
        "requisição concluída",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "duration_ms": round((time.perf_counter() - inicio) * 1000, 2),
        },
        exc_info=com_excecao,
    )


def configurar_observabilidade(app: FastAPI, servico: str) -> None:
    configurar_logging(servico, os.getenv("LOG_LEVEL", "INFO"))

    @app.middleware("http")
    async def observabilidade(request: Request, call_next):
        cid = request.headers.get(correlation.HEADER) or correlation.gerar()
        token = correlation.definir(cid)
        inicio = time.perf_counter()
        try:
            resposta = await call_next(request)
        except Exception:
            _registrar(request, 500, inicio, com_excecao=True)
            raise
        else:
            resposta.headers[correlation.HEADER] = cid
            _registrar(request, resposta.status_code, inicio)
            return resposta
        finally:
            correlation.resetar(token)