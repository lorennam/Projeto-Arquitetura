from enum import Enum

class TipoRegistro(str, Enum):
    ANOTACAO = "anotacao"
    EXAME = "exame"
    PRESCRICAO = "prescricao"