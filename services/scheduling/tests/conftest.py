import sys
from pathlib import Path

# O Dockerfile copia app/ para a raiz do container, então os módulos são
# importados "soltos" (from schemas import ...). Replicamos isso nos testes.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from repository import repositorio  # noqa: E402


@pytest.fixture(autouse=True)
def limpa_repositorio():
    """Isola os testes: o repositório em memória é um singleton do módulo."""
    repositorio._consultas.clear()
    yield
    repositorio._consultas.clear()


@pytest.fixture
def client():
    return TestClient(app)