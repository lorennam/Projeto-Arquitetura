import httpx
from .config import CONNECT_TIMEOUT, REQUEST_TIMEOUT, SERVICES

from .correlation import CORRELATION_HEADER, get_correlation_id
from fastapi import APIRouter, HTTPException, Request, Response


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

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                request.method,
                f"{base_url}/{path}",
                params=request.query_params,
                content=await request.body(),
                headers=headers,
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Tempo esgotado ao chamar '{service}'")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail=f"Serviço '{service}' indisponível")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )