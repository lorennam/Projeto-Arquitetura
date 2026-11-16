from fastapi import FastAPI

from observability import configurar_observabilidade

app = FastAPI(
    title="Notification Service",
    description="Serviço de gerenciamento de notificações de saúde",
    version="0.1.0"
)

configurar_observabilidade(app, "notification")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "notification"
    }