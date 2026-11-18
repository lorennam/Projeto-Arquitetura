from typing import List
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, status
from producer import publicar_consulta_agendada
from enums import StatusConsulta
from erros import ErroResponse
from repository import repositorio
from schemas import ConsultaCreate, ConsultaResponse
from prometheus_fastapi_instrumentator import Instrumentator

from observability import configurar_observabilidade

app = FastAPI(
    title="Scheduling Service",
    description="Serviço de gerenciamento de agendamentos médicos",
    version="0.1.0"
)
Instrumentator().instrument(app).expose(app)

configurar_observabilidade(app, "scheduling")

RESP_422 = {422: {"description": "Dados inválidos (ex.: id malformado ou data_hora no passado)"}}
RESP_404 = {404: {"model": ErroResponse, "description": "Consulta não encontrada"}}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "scheduling"
    }


@app.post(
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

    #Publica os dados da consulta no RabbitMQ com o ID de correlaão
    publicar_consulta_agendada(
        consulta,
        id_correlacao,
        str(consulta.id)
    )

    
    return consulta

@app.get(
    "/consultas",
    response_model=List[ConsultaResponse],
    summary="Lista todas as consultas",
    tags=["Consultas"],
    responses={200: {"description": "Lista de consultas (vazia se não houver nenhuma)"}},
)
def listar_consultas():
    return repositorio.listar()


@app.get(
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


@app.post(
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