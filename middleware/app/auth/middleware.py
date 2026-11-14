import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .bearer import extract_bearer_token
from .public_routes import is_public
from .tokens import decode_token


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Preflight CORS não leva token; deixa passar.
        if request.method == "OPTIONS" or is_public(request.url.path):
            return await call_next(request)

        token = extract_bearer_token(request.headers.get("Authorization"))
        if token is None:
            return _unauthorized("Token de autenticação ausente")

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return _unauthorized("Token expirado")
        except jwt.InvalidTokenError:
            return _unauthorized("Token inválido")

        # Garante que o token tem as claims que o gateway espera.
        username = payload.get("sub")
        role = payload.get("role")
        if not username or not role:
            return _unauthorized("Token inválido")

        # Identidade validada, disponível para o resto da requisição.
        request.state.user = {"username": username, "role": role}

        return await call_next(request)