
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models import Paciente
from schemas import PacienteCreate, PacienteUpdate


class PacienteRepository:

    def criar(self, db: Session, dados: PacienteCreate) -> Paciente:
        paciente = Paciente(**dados.model_dump())

        db.add(paciente)
        db.commit()
        db.refresh(paciente)

        return paciente

    def listar(self, db: Session) -> list[Paciente]:
        return db.query(Paciente).order_by(Paciente.nome).all()

    def obter(self, db: Session, paciente_id: UUID) -> Optional[Paciente]:
        return db.query(Paciente).filter(
            Paciente.id == paciente_id
        ).first()

    def obter_por_cpf(self, db: Session, cpf: str) -> Optional[Paciente]:
        return db.query(Paciente).filter(
            Paciente.cpf == cpf
        ).first()

    def atualizar(
        self,
        db: Session,
        paciente: Paciente,
        dados: PacienteUpdate,
    ) -> Paciente:
        atualizacoes = dados.model_dump(exclude_unset=True)

        for campo, valor in atualizacoes.items():
            setattr(paciente, campo, valor)

        db.commit()
        db.refresh(paciente)

        return paciente

    def excluir(self, db: Session, paciente: Paciente) -> None:
        db.delete(paciente)
        db.commit()


repositorio = PacienteRepository()
