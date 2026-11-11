from fastapi import FastAPI, status

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