from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from enums import StatusConsulta


class ConsultaCreate(BaseModel):
    paciente_id: str
    profissional_id: str
    data_hora: datetime
    motivo: Optional[str] = None


class ConsultaResponse(ConsultaCreate):
    id: UUID
    status: StatusConsulta
    criado_em: datetime