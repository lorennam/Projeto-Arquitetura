from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from enums import StatusConsulta


class ConsultaCreate(BaseModel):
    paciente_id: str = Field(..., examples=["paciente-001"])
    profissional_id: str = Field(..., examples=["medico-001"])
    data_hora: datetime = Field(
        ...,
        description="Data e hora da consulta (deve estar no futuro). Sem fuso, assume UTC.",
        examples=["2030-05-20T14:30:00Z"],
    )
    motivo: Optional[str] = Field(None, examples=["Consulta de rotina"])

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
    id: UUID = Field(..., examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    status: StatusConsulta = Field(..., examples=["agendada"])
    criado_em: datetime = Field(..., examples=["2026-11-13T20:58:00Z"])