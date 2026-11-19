
from uuid import UUID
from sqlalchemy import text

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Paciente
from repository import repositorio
from schemas import PacienteCreate, PacienteResponse, PacienteUpdate
from prometheus_fastapi_instrumentator import Instrumentator

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Patient Extra Point",
    description="Microsserviço responsável pelo cadastro e gerenciamento de pacientes.",
    version="1.0.0",
)

Instrumentator().instrument(app).expose(app)
@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "patient_extra_point",
            "database": "connected",
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível",
        )


@app.get(
    "/v1/pacientes",
    response_model=list[PacienteResponse],
    tags=["Pacientes"],
)
def listar_pacientes(db: Session = Depends(get_db)):
    return repositorio.listar(db)


@app.get(
    "/v1/pacientes/{paciente_id}",
    response_model=PacienteResponse,
    tags=["Pacientes"],
)
def obter_paciente(
    paciente_id: UUID,
    db: Session = Depends(get_db),
):
    paciente = repositorio.obter(db, paciente_id)

    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado",
        )

    return paciente


@app.post(
    "/v1/pacientes",
    response_model=PacienteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Pacientes"],
)
def cadastrar_paciente(
    dados: PacienteCreate,
    db: Session = Depends(get_db),
):
    if repositorio.obter_por_cpf(db, dados.cpf):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um paciente cadastrado com este CPF",
        )

    try:
        return repositorio.criar(db, dados)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um paciente cadastrado com este CPF",
        )


@app.put(
    "/v1/pacientes/{paciente_id}",
    response_model=PacienteResponse,
    tags=["Pacientes"],
)
def atualizar_paciente(
    paciente_id: UUID,
    dados: PacienteUpdate,
    db: Session = Depends(get_db),
):
    paciente = repositorio.obter(db, paciente_id)

    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado",
        )

    return repositorio.atualizar(db, paciente, dados)


@app.delete(
    "/v1/pacientes/{paciente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Pacientes"],
)
def excluir_paciente(
    paciente_id: UUID,
    db: Session = Depends(get_db),
):
    paciente = repositorio.obter(db, paciente_id)

    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado",
        )

    repositorio.excluir(db, paciente)
