"""Adaptador de correlation_id para o middleware.

O gateway (Anna) já gera e propaga o X-Correlation-ID em gateway/correlation.py.
Este módulo expõe a mesma interface usada nos outros serviços (logging_json.py e
observability.py), mas reaproveita o ContextVar do gateway, para existir um único
correlation_id por requisição.
"""
import logging

from gateway.correlation import (
    CORRELATION_HEADER as HEADER,
    correlation_id_var,
    get_correlation_id,
    new_correlation_id,
)


def gerar() -> str:
    # Dentro do CorrelationIdMiddleware o id já existe: reaproveita em vez de gerar outro.
    atual = get_correlation_id()
    return new_correlation_id() if atual == "-" else atual


def definir(cid: str):
    return correlation_id_var.set(cid)


def resetar(token) -> None:
    correlation_id_var.reset(token)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True