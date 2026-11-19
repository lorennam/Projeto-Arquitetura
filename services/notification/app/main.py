from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


from observability import configurar_observabilidade

app = FastAPI(
    title="Notification Service",
    description="Serviço de gerenciamento de notificações de saúde",
    version="0.1.0"
)

Instrumentator().instrument(app).expose(app)
configurar_observabilidade(app, "notification")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "notification"
    }