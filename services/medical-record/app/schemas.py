from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enums import TipoRegistro

DESCRICAO_MAX = 2000


class RegistroCreate(BaseModel):
    profissional_id: str
    tipo: TipoRegistro
    descricao: str = Field(..., max_length=DESCRICAO_MAX)
    consulta_id: Optional[str] = None

    @field_validator("descricao")
    @classmethod
    def descricao_nao_vazia(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("descricao não pode ser vazia")
        return valor


class RegistroResponse(RegistroCreate):
    id: UUID
    paciente_id: str
    criado_em: datetime