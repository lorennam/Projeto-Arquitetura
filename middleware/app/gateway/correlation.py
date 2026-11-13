import uuid
from contextvars import ContextVar

CORRELATION_HEADER = "X-Correlation-ID"

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return correlation_id_var.get()


def new_correlation_id() -> str:
    return str(uuid.uuid4())