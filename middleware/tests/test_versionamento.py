import sys
from pathlib import Path

# Permite importar o pacote `auth` a partir de middleware/app
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from auth.permissions import is_allowed, service_from_path  # noqa: E402


def test_servico_e_extraido_independente_da_versao():
    assert service_from_path("/api/scheduling/v1/consultas") == "scheduling"
    assert service_from_path("/api/scheduling/v2/consultas") == "scheduling"
    assert service_from_path("/api/medical-record/v1/pacientes/p-1/registros") == "medical-record"


def test_paciente_pode_criar_consulta_nas_duas_versoes():
    assert is_allowed("patient", "scheduling", "POST")


def test_paciente_nao_acessa_prontuario_em_nenhuma_versao():
    assert not is_allowed("patient", "medical-record", "GET")


def test_rotas_fora_de_api_nao_tem_servico():
    assert service_from_path("/auth/login") is None
    assert service_from_path("/health") is None