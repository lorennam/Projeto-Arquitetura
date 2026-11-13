import asyncio

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from .config import (
    BACKOFF_BASE_SECONDS,
    CONNECT_TIMEOUT,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    SERVICES,
)

from .correlation import CORRELATION_HEADER, get_correlation_id
router = APIRouter(prefix="/api")


@router.api_route(
    "/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(service: str, path: str, request: Request):
    base_url = SERVICES.get(service)
    if not base_url:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

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
        if isinstance(last_error, httpx.TimeoutException):
            raise HTTPException(status_code=504, detail=f"Tempo esgotado ao chamar '{service}'")
        raise HTTPException(status_code=503, detail=f"Serviço '{service}' indisponível")
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )