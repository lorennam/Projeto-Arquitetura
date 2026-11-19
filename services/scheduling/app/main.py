from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, FastAPI, Header, HTTPException, status
from producer import publicar_consulta_agendada
from enums import StatusConsulta
from erros import ErroResponse
from repository import repositorio
from schemas import (
    ConsultaCreate,
    ConsultaCreateV2,
    ConsultaResponse,
    ConsultaResponseV2,
)
from prometheus_fastapi_instrumentator import Instrumentator
from grpc_client import paciente_tem_prontuario

from observability import configurar_observabilidade
from tracing import configurar_tracing

app = FastAPI(
    title="Scheduling Service",
    description="Serviço de gerenciamento de agendamentos médicos",
    version="0.1.0"
)
Instrumentator().instrument(app).expose(app)

configurar_observabilidade(app, "scheduling")
configurar_tracing(app, "scheduling")

RESP_422 = {422: {"description": "Dados inválidos (ex.: id malformado ou data_hora no passado)"}}
RESP_404 = {404: {"model": ErroResponse, "description": "Consulta não encontrada"}}
# Rotas de negócio sob /v1. O /health e o /metrics ficam fora do prefixo
# porque são rotas de infraestrutura, não parte do contrato versionado.
v1 = APIRouter(prefix="/v1")
# v2: mesma operação, payload com `inicio` no lugar de `data_hora`.
v2 = APIRouter(prefix="/v2")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "scheduling"
    }


@v1.post(
    "/consultas",
    response_model=ConsultaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma consulta",
    tags=["Consultas"],
    responses={
        201: {"description": "Consulta criada com status 'agendada'"},
        409: {
            "model": ErroResponse,
            "description": "Profissional já possui consulta agendada nesse horário",
        },
        **RESP_422,
    },
)

def criar_consulta(
    dados: ConsultaCreate,
    correlation_id: str = Header(default=None, alias="X-Correlation-ID")
):
    """Cria uma consulta e publcia o evento correspondente no RabbitMQ.

    Recebe os dados da consulta e o identificador de correlação enviado pelo middleware.
    Após verificar conflitos e salvar a consulta no repositório, publica o evento consulta.agendada.

    Caso não receba um correlation_id, gera um novo identificador UUID.
    """
    
    if repositorio.existe_conflito(dados.profissional_id, dados.data_hora):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profissional já possui consulta agendada nesse horário.",
        )
    #Persiste a consulta antes de publicar o evento.
    consulta = repositorio.criar(dados)

    #Reutiliza o ID recebido do middleware ou gera um novo UUID
    id_correlacao = correlation_id or str(uuid4())
    
    # Chamada interna gRPC: informativa, não bloqueia o agendamento.
    paciente_tem_prontuario(dados.paciente_id, id_correlacao)
    
    #Publica os dados da consulta no RabbitMQ com o ID de correlaão
    publicar_consulta_agendada(
        consulta,
        id_correlacao,
        str(consulta.id)
    )

    
    return consulta

@v1.get(
    "/consultas",
    response_model=List[ConsultaResponse],
    summary="Lista todas as consultas",
    tags=["Consultas"],
    responses={200: {"description": "Lista de consultas (vazia se não houver nenhuma)"}},
)
def listar_consultas():
    return repositorio.listar()


@v1.get(
    "/consultas/{consulta_id}",
    response_model=ConsultaResponse,
    summary="Consulta uma consulta pelo id",
    tags=["Consultas"],
    responses={200: {"description": "Consulta encontrada"}, **RESP_404, **RESP_422},
)
def obter_consulta(consulta_id: UUID):
    consulta = repositorio.obter(consulta_id)
    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )
    return consulta


@v1.post(
    "/consultas/{consulta_id}/cancelamento",
    response_model=ConsultaResponse,
    summary="Cancela uma consulta",
    tags=["Consultas"],
    responses={
        200: {"description": "Consulta cancelada (status 'cancelada')"},
        409: {"model": ErroResponse, "description": "Consulta já está cancelada"},
        **RESP_404,
        **RESP_422,
    },
)
def cancelar_consulta(consulta_id: UUID):
    consulta = repositorio.obter(consulta_id)
    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )
    if consulta.status == StatusConsulta.CANCELADA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consulta já está cancelada",
        )
    return repositorio.cancelar(consulta_id)

@v2.post(
    "/consultas",
    response_model=ConsultaResponseV2,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma consulta (v2)",
    description="Versão 2: o campo `data_hora` da v1 passou a se chamar `inicio`.",
    tags=["Consultas v2"],
    responses={
        201: {"description": "Consulta criada com status 'agendada'"},
        409: {
            "model": ErroResponse,
            "description": "Profissional já possui consulta agendada nesse horário",
        },
        **RESP_422,
    },
)
def criar_consulta_v2(
    dados: ConsultaCreateV2,
    correlation_id: str = Header(default=None, alias="X-Correlation-ID"),
):
    # Reaproveita o fluxo da v1 (conflito, gRPC e evento no RabbitMQ).
    dados_v1 = ConsultaCreate(
        paciente_id=dados.paciente_id,
        profissional_id=dados.profissional_id,
        data_hora=dados.inicio,
        motivo=dados.motivo,
    )
    consulta = criar_consulta(dados_v1, correlation_id)
    return ConsultaResponseV2(
        id=consulta.id,
        status=consulta.status,
        criado_em=consulta.criado_em,
        paciente_id=consulta.paciente_id,
        profissional_id=consulta.profissional_id,
        inicio=consulta.data_hora,
        motivo=consulta.motivo,
    )


app.include_router(v1)
app.include_router(v2)