"""Logs estruturados em JSON (uma linha por evento), usando só a biblioteca padrão."""
import json
import logging
import sys
from datetime import datetime, timezone

from correlation import CorrelationIdFilter

# Campos extras que, se presentes no log, entram no JSON.
CAMPOS_EXTRAS = ("correlation_id", "method", "path", "status", "duration_ms")


class JsonFormatter(logging.Formatter):
    def __init__(self, servico: str) -> None:
        super().__init__()
        self.servico = servico

    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.servico,
            "message": record.getMessage(),
        }
        for campo in CAMPOS_EXTRAS:
            valor = getattr(record, campo, None)
            if valor is not None:
                dados[campo] = valor
        if record.exc_info:
            dados["exception"] = self.formatException(record.exc_info)
        return json.dumps(dados, ensure_ascii=False)


def configurar_logging(servico: str, nivel: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(servico))
    handler.addFilter(CorrelationIdFilter())

    raiz = logging.getLogger()
    raiz.handlers = [handler]
    raiz.setLevel(nivel)

    # Os logs do uvicorn passam a sair em JSON pelo logger raiz.
    for nome in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(nome)
        logger.handlers = []
        logger.propagate = True
    # O access log do uvicorn é substituído pelo log do middleware (com correlation_id e duração).
    logging.getLogger("uvicorn.access").disabled = True