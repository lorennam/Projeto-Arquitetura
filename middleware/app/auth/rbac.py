from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .permissions import is_allowed, service_from_path


class RBACMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Preflight CORS não leva token; deixa passar.
        if request.method == "OPTIONS":
            return await call_next(request)

        service = service_from_path(request.url.path)

        # Só rotas de serviço (/api/<servico>/...) passam pela tabela.
        # Rotas públicas e /auth/* já são tratadas pelo middleware de JWT.
        if service is None:
            return await call_next(request)

        user = getattr(request.state, "user", None)
        if user is None:
            # Não deveria acontecer (o JWT roda antes), mas se acontecer, nega.
            return JSONResponse(
                status_code=401,
                content={"detail": "Token de autenticação ausente"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not is_allowed(user["role"], service, request.method):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Papel '{user['role']}' sem permissão para "
                              f"{request.method} em '{service}'"
                },
            )

        return await call_next(request)