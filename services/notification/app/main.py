from fastapi import FastAPI

app = FastAPI(
    title="Notification Service",
    description="Serviço de gerenciamento de notificações de saúde",
    version="0.1.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "notification"
    }