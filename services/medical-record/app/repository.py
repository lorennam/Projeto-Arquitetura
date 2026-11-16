from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from enums import TipoRegistro
from schemas import RegistroCreate, RegistroResponse


class ProntuarioRepository:
    """Armazenamento em memória dos prontuários (some ao reiniciar o container).

    Cada paciente tem uma lista de registros, na ordem em que foram adicionados.
    """

    def __init__(self) -> None:
        self._prontuarios: Dict[str, List[RegistroResponse]] = {}

    def adicionar(self, paciente_id: str, dados: RegistroCreate) -> RegistroResponse:
        registro = RegistroResponse(
            id=uuid4(),
            paciente_id=paciente_id,
            criado_em=datetime.now(timezone.utc),
            **dados.model_dump(),
        )
        self._prontuarios.setdefault(paciente_id, []).append(registro)
        return registro

    def listar(
        self, paciente_id: str, tipo: Optional[TipoRegistro] = None
    ) -> List[RegistroResponse]:
        registros = self._prontuarios.get(paciente_id, [])
        return [r for r in registros if tipo is None or r.tipo == tipo]

    def obter(self, paciente_id: str, registro_id: UUID) -> Optional[RegistroResponse]:
        return next(
            (r for r in self._prontuarios.get(paciente_id, []) if r.id == registro_id),
            None,
        )


repositorio = ProntuarioRepository()