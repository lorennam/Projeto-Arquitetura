from enum import Enum


class StatusConsulta(str, Enum):
    AGENDADA = "agendada"
    CANCELADA = "cancelada"