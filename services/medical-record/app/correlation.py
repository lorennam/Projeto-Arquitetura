"""Contexto de correlation_id da requisição atual.

O gateway gera o X-Correlation-ID e repassa aos serviços. Se o header não vier
(chamada direta ao serviço), o serviço gera um novo UUID.
"""
import logging
from contextvars import ContextVar, Token
from typing import Optional
from uuid import uuid4

HEADER = "X-Correlation-ID"

_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def gerar() -> str:
    return str(uuid4())


def obter() -> Optional[str]:
    return _correlation_id.get()


def definir(valor: str) -> Token:
    return _correlation_id.set(valor)


def resetar(token: Token) -> None:
    _correlation_id.reset(token)


class CorrelationIdFilter(logging.Filter):
    """Acrescenta o correlation_id atual a todo log emitido durante a requisição."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "correlation_id", None) is None:
            record.correlation_id = obter()
        return True