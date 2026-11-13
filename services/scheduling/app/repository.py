from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from enums import StatusConsulta
from schemas import ConsultaCreate, ConsultaResponse


class ConsultaRepository:
    """Armazenamento em memória das consultas (some ao reiniciar o container)."""

    def __init__(self) -> None:
        self._consultas: Dict[UUID, ConsultaResponse] = {}

    def criar(self, dados: ConsultaCreate) -> ConsultaResponse:
        consulta = ConsultaResponse(
            id=uuid4(),
            status=StatusConsulta.AGENDADA,
            criado_em=datetime.now(timezone.utc),
            **dados.model_dump(),
        )
        self._consultas[consulta.id] = consulta
        return consulta

    def obter(self, consulta_id: UUID) -> Optional[ConsultaResponse]:
        return self._consultas.get(consulta_id)

    def listar(self) -> List[ConsultaResponse]:
        return list(self._consultas.values())

    def cancelar(self, consulta_id: UUID) -> Optional[ConsultaResponse]:
        consulta = self._consultas.get(consulta_id)
        if consulta is None:
            return None
        cancelada = consulta.model_copy(update={"status": StatusConsulta.CANCELADA})
        self._consultas[consulta_id] = cancelada
        return cancelada

    def existe_conflito(self, profissional_id: str, data_hora: datetime) -> bool:
        """Há consulta agendada do mesmo profissional exatamente nesse horário?"""
        return any(
            c.status == StatusConsulta.AGENDADA
            and c.profissional_id == profissional_id
            and c.data_hora == data_hora
            for c in self._consultas.values()
        )


repositorio = ConsultaRepository()