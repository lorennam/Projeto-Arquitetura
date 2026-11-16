from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from enums import TipoRegistro


class RegistroCreate(BaseModel):
    profissional_id: str
    tipo: TipoRegistro
    descricao: str
    consulta_id: Optional[str] = None


class RegistroResponse(RegistroCreate):
    id: UUID
    paciente_id: str
    criado_em: datetime