
from fastapi import FastAPI

app = FastAPI(
    title="Health Middleware",
    description="Middleware distribuído para integração de serviços de saúde",
    version="0.1.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "middleware"
    }