from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from enums import StatusConsulta


class ConsultaCreate(BaseModel):
    paciente_id: str
    profissional_id: str
    data_hora: datetime
    motivo: Optional[str] = None

    @field_validator("data_hora")
    @classmethod
    def data_hora_no_futuro(cls, valor: datetime) -> datetime:
        # Se vier sem fuso horário, assume UTC
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        if valor <= datetime.now(timezone.utc):
            raise ValueError("data_hora deve estar no futuro")
        return valor


class ConsultaResponse(ConsultaCreate):
    id: UUID
    status: StatusConsulta
    criado_em: datetime