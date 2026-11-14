from fastapi import FastAPI

from auth.middleware import JWTAuthMiddleware
from auth.router import router as auth_router
from gateway.correlation import CorrelationIdMiddleware
from gateway.router import router as gateway_router

app = FastAPI(
    title="Health Middleware",
    description="Middleware distribuído para integração de serviços de saúde",
    version="0.1.0"
)

# Ordem importa no Starlette: o último adicionado é o mais externo.
# Auth primeiro, Correlation depois, para o Correlation envolver o Auth
# e o 401 também sair com o X-Correlation-ID.
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(auth_router)
app.include_router(gateway_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "middleware"
    }