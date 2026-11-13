import hashlib
import hmac
import os

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


USERS = {
    "paciente": {"password_hash": _hash(os.environ["PATIENT_PASSWORD"]), "role": "patient"},
    "medico": {"password_hash": _hash(os.environ["DOCTOR_PASSWORD"]), "role": "doctor"},
    "admin": {"password_hash": _hash(os.environ["ADMIN_PASSWORD"]), "role": "admin"},
}


def authenticate(username: str, password: str):
    """Retorna {"username", "role"} se as credenciais forem válidas, senão None."""
    user = USERS.get(username)
    if user is None:
        return None
    if not hmac.compare_digest(user["password_hash"], _hash(password)):
        return None
    return {"username": username, "role": user["role"]}