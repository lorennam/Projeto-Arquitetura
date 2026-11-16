from fastapi import FastAPI

from auth.middleware import JWTAuthMiddleware
from auth.router import router as auth_router
from gateway.correlation import CorrelationIdMiddleware
from gateway.router import router as gateway_router
from auth.rbac import RBACMiddleware
from observability import configurar_observabilidade

app = FastAPI(
    title="Health Middleware",
    description="Middleware distribuído para integração de serviços de saúde",
    version="0.1.0"
)

# Ordem importa no Starlette: o último adicionado é o mais externo.
# Execução: Correlation -> JWT -> RBAC -> rota.
# - Correlation envolve tudo, então 401 e 403 também saem com X-Correlation-ID.
# - JWT preenche request.state.user, que o RBAC consome.
app.add_middleware(RBACMiddleware)
app.add_middleware(JWTAuthMiddleware)
configurar_observabilidade(app, "middleware")
app.add_middleware(CorrelationIdMiddleware)

app.include_router(auth_router)
app.include_router(gateway_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "middleware"
    }