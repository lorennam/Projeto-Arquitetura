from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .config import JWT_EXPIRES_MINUTES
from .tokens import create_access_token
from .users import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    user = authenticate(body.username, body.password)
    if user is None:
        # Mesma resposta para usuário inexistente e senha errada
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_access_token(user["username"], user["role"])
    return LoginResponse(
        access_token=token,
        expires_in=JWT_EXPIRES_MINUTES * 60,
    )