from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from enums import TipoRegistro

DESCRICAO_MAX = 2000


class RegistroCreate(BaseModel):
    profissional_id: str = Field(..., examples=["medico-001"])
    tipo: TipoRegistro = Field(..., examples=["exame"])
    descricao: str = Field(
        ...,
        max_length=DESCRICAO_MAX,
        description="Texto do registro. Espaços nas pontas são removidos; não pode ser vazio.",
        examples=["Hemograma completo sem alterações"],
    )
    consulta_id: Optional[str] = Field(
        None,
        description="Id da consulta (scheduling) à qual o registro se refere. Apenas armazenado, não validado.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )

    @field_validator("descricao")
    @classmethod
    def descricao_nao_vazia(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("descricao não pode ser vazia")
        return valor


class RegistroResponse(RegistroCreate):
    id: UUID = Field(..., examples=["9b2f6d1e-4c3a-4f5b-8a7d-1e2f3a4b5c6d"])
    paciente_id: str = Field(..., examples=["paciente-001"])
    criado_em: datetime = Field(..., examples=["2026-11-15T21:34:00Z"])