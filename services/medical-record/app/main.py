from fastapi import FastAPI, status
from repository import repositorio
from schemas import RegistroCreate, RegistroResponse

app = FastAPI(
    title="Medical Record Service",
    description="Serviço de gerenciamento de prontuários médicos",
    version="0.1.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "medical-record"
    }


@app.post(
    "/pacientes/{paciente_id}/registros",
    response_model=RegistroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona um registro ao prontuário do paciente",
)
def adicionar_registro(paciente_id: str, dados: RegistroCreate):
    return repositorio.adicionar(paciente_id, dados)