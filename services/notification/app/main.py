from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from observability import configurar_observabilidade
from tracing import configurar_tracing

app = FastAPI(
    title="Notification Service",
    description="Serviço de gerenciamento de notificações de saúde",
    version="0.1.0"
)

Instrumentator().instrument(app).expose(app)
configurar_observabilidade(app, "notification")
configurar_tracing(app, "notification")