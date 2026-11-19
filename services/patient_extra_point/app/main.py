
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import Depends, FastAPI, HTTPException, status
from prometheus_fastapi_instrumentator import Instrumentator

from database import Base, engine, get_db
from models import Paciente
from repository import repositorio
from schemas import PacienteCreate, PacienteResponse, PacienteUpdate
from observability import configurar_observabilidade


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Patient Extra Point",
    description="Microsserviço responsável pelo cadastro e gerenciamento de pacientes.",
    version="1.0.0",
)

Instrumentator().instrument(app).expose(app)
configurar_observabilidade(app, "patient-extra-point")


@app.get(
    "/health",
    tags=["Health"],
    summary="Verificar saúde do serviço",
    description="Verifica a disponibilidade da API e a conexão com o banco de dados.",
    responses={
        200: {"description": "Serviço e banco de dados disponíveis."},
        503: {"description": "Banco de dados indisponível."},
    },
)
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
    summary="Listar pacientes",
    description="Retorna a lista de pacientes cadastrados.",
    responses={
        200: {"description": "Lista de pacientes retornada com sucesso."},
    },
)
def listar_pacientes(db: Session = Depends(get_db)):
    return repositorio.listar(db)


@app.get(
    "/v1/pacientes/{paciente_id}",
    response_model=PacienteResponse,
    tags=["Pacientes"],
    summary="Obter paciente",
    description="Busca os dados de um paciente pelo seu identificador.",
    responses={
        200: {"description": "Paciente encontrado."},
        404: {"description": "Paciente não encontrado."},
    },
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
    summary="Cadastrar paciente",
    description="Cadastra um novo paciente. O CPF deve ser único.",
    responses={
        201: {"description": "Paciente cadastrado com sucesso."},
        409: {"description": "Já existe um paciente cadastrado com este CPF."},
    },
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
    summary="Atualizar paciente",
    description="Atualiza os dados de um paciente existente.",
    responses={
        200: {"description": "Paciente atualizado com sucesso."},
        404: {"description": "Paciente não encontrado."},
    },
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
    summary="Excluir paciente",
    description="Remove um paciente cadastrado pelo seu identificador.",
    responses={
        204: {"description": "Paciente excluído com sucesso."},
        404: {"description": "Paciente não encontrado."},
    },
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
