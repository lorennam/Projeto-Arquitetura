
from fastapi import FastAPI, Query
from prometheus_fastapi_instrumentator import Instrumentator
import asyncio

from auth.middleware import JWTAuthMiddleware
from auth.router import router as auth_router
from gateway.correlation import CorrelationIdMiddleware
from gateway.router import router as gateway_router

app = FastAPI(
    title="Health Middleware",
    description="Middleware distribuído para integração de serviços de saúde",
    version="0.1.0"
)

# Primeiro adicionamos os middlewares da aplicação.
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# O Instrumentator é adicionado por último para ficar
# mais externo e também observar respostas 401 e 403.
Instrumentator().instrument(app).expose(app)

app.include_router(auth_router)
app.include_router(gateway_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "middleware"
    }


# Rota para testes de latência do Grafana
@app.get("/test/latency")
async def test_latency(delay: float = Query(default=0, ge=0, le=5)):
    await asyncio.sleep(delay)
    return {
        "status": "ok",
        "delay_seconds": delay
    }
