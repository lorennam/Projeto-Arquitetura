from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Query, status

from enums import TipoRegistro
from erros import ErroResponse
from repository import repositorio
from schemas import RegistroCreate, RegistroResponse
from observability import configurar_observabilidade

app = FastAPI(
    title="Medical Record Service",
    description="Serviço de gerenciamento de prontuários médicos",
    version="0.1.0"
)

configurar_observabilidade(app, "medical-record")

# Todas as rotas de negócio ficam sob /v1. O /health fica fora do prefixo
# porque é rota de infraestrutura (healthcheck), não parte do contrato versionado.
v1 = APIRouter(prefix="/v1", tags=["Prontuário"])

RESP_422 = {
    422: {"description": "Dados inválidos (ex.: descrição vazia, tipo desconhecido ou id malformado)"}
}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "medical-record"
    }


@v1.post(
    "/pacientes/{paciente_id}/registros",
    response_model=RegistroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona um registro ao prontuário do paciente",
    responses={
        201: {"description": "Registro adicionado ao prontuário"},
        **RESP_422,
    },
)
def adicionar_registro(paciente_id: str, dados: RegistroCreate):
    return repositorio.adicionar(paciente_id, dados)


@v1.get(
    "/pacientes/{paciente_id}/registros",
    response_model=List[RegistroResponse],
    summary="Consulta o prontuário do paciente",
    responses={
        200: {"description": "Registros do paciente (lista vazia se não houver nenhum)"},
        **RESP_422,
    },
)
def consultar_prontuario(
    paciente_id: str,
    tipo: Optional[TipoRegistro] = Query(None, description="Filtra por tipo de registro"),
):
    return repositorio.listar(paciente_id, tipo)


@v1.get(
    "/pacientes/{paciente_id}/registros/{registro_id}",
    response_model=RegistroResponse,
    summary="Consulta um registro específico do prontuário",
    responses={
        200: {"description": "Registro encontrado"},
        404: {
            "model": ErroResponse,
            "description": "Registro não encontrado (ou pertence a outro paciente)",
        },
        **RESP_422,
    },
)
def obter_registro(paciente_id: str, registro_id: UUID):
    registro = repositorio.obter(paciente_id, registro_id)
    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado",
        )
    return registro


app.include_router(v1)