from uuid import UUID
from fastapi import FastAPI, HTTPException, status
from repository import repositorio
from schemas import ConsultaCreate, ConsultaResponse

app = FastAPI(
    title="Scheduling Service",
    description="Serviço de gerenciamento de agendamentos médicos",
    version="0.1.0"
)

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
)
def criar_consulta(dados: ConsultaCreate):
    return repositorio.criar(dados)


@app.get(
    "/consultas/{consulta_id}",
    response_model=ConsultaResponse,
    summary="Consulta uma consulta pelo id",
)
def obter_consulta(consulta_id: UUID):
    consulta = repositorio.obter(consulta_id)
    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )
    return consulta