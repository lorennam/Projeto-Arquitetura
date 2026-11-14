import asyncio

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from .circuit_breaker import CircuitBreaker
from .config import (
    BACKOFF_BASE_SECONDS,
    CB_FAILURE_THRESHOLD,
    CB_RECOVERY_SECONDS,
    CONNECT_TIMEOUT,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    SERVICES,
)
from .correlation import CORRELATION_HEADER, get_correlation_id
from auth.internal_headers import build_internal_headers, strip_internal_headers

router = APIRouter(prefix="/api")

breakers = {
    name: CircuitBreaker(CB_FAILURE_THRESHOLD, CB_RECOVERY_SECONDS)
    for name in SERVICES
}


@router.api_route(
    "/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(service: str, path: str, request: Request):
    base_url = SERVICES.get(service)
    if not base_url:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    breaker = breakers[service]
    if not breaker.allow_request():
        raise HTTPException(
            status_code=503,
            detail=f"Serviço '{service}' temporariamente indisponível. Tente novamente em instantes.",
            headers={"Retry-After": str(int(CB_RECOVERY_SECONDS))},
        )

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    # Anti-spoofing: descarta X-User-* vindo do cliente e injeta a identidade
    # validada pelo middleware de autenticação.
    headers = strip_internal_headers(headers)
    user = getattr(request.state, "user", None)
    if user:
        headers.update(build_internal_headers(user))

    headers[CORRELATION_HEADER] = get_correlation_id()

    timeout = httpx.Timeout(REQUEST_TIMEOUT, connect=CONNECT_TIMEOUT)

    body = await request.body()
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    request.method,
                    f"{base_url}/{path}",
                    params=request.query_params,
                    content=body,
                    headers=headers,
                )
            break
        except httpx.RequestError as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))
    else:
        breaker.record_failure()
        if isinstance(last_error, httpx.TimeoutException):
            raise HTTPException(status_code=504, detail=f"Tempo esgotado ao chamar '{service}'")
        raise HTTPException(status_code=503, detail=f"Serviço '{service}' indisponível")

    breaker.record_success()

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )