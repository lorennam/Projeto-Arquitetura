from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


app = FastAPI(
    title="Notification Service",
    description="Serviço de gerenciamento de notificações de saúde",
    version="0.1.0"
)
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "notification"
    }