from pydantic import BaseModel, Field


class ErroResponse(BaseModel):
    """Formato das respostas de erro de negócio (404)."""

    detail: str = Field(..., examples=["Registro não encontrado"])