
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class PacienteCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    cpf: str = Field(..., min_length=11, max_length=14)
    data_nascimento: date
    email: Optional[EmailStr] = None
    telefone: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = Field(None, max_length=255)

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("nome não pode ser vazio")
        return valor

    @field_validator("cpf")
    @classmethod
    def normalizar_cpf(cls, valor: str) -> str:
        cpf = "".join(caractere for caractere in valor if caractere.isdigit())

        if len(cpf) != 11:
            raise ValueError("CPF deve conter 11 dígitos")

        return cpf


class PacienteUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=150)
    data_nascimento: Optional[date] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = Field(None, max_length=255)

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return valor

        valor = valor.strip()
        if not valor:
            raise ValueError("nome não pode ser vazio")
        return valor


class PacienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    cpf: str
    data_nascimento: date
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    criado_em: datetime
    atualizado_em: datetime
