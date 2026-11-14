from pydantic import BaseModel, Field


class ErroResponse(BaseModel):
    """Formato das respostas de erro de negócio (404 e 409)."""

    detail: str = Field(..., examples=["Consulta não encontrada"])