from datetime import datetime, timedelta, timezone
from uuid import uuid4


def horario_futuro(dias=7):
    return (datetime.now(timezone.utc) + timedelta(days=dias)).replace(microsecond=0)


def payload(**alteracoes):
    dados = {
        "paciente_id": "paciente-001",
        "profissional_id": "medico-001",
        "data_hora": horario_futuro().isoformat(),
        "motivo": "Consulta de rotina",
    }
    dados.update(alteracoes)
    return dados


def cria(client, **alteracoes):
    return client.post("/consultas", json=payload(**alteracoes))


# ---------- criação ----------

def test_criar_consulta_retorna_201_e_status_agendada(client):
    resposta = cria(client)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "agendada"
    assert corpo["paciente_id"] == "paciente-001"
    assert corpo["profissional_id"] == "medico-001"
    assert corpo["id"]
    assert corpo["criado_em"]


def test_criar_sem_campo_obrigatorio_retorna_422(client):
    dados = payload()
    del dados["paciente_id"]

    resposta = client.post("/consultas", json=dados)

    assert resposta.status_code == 422


def test_criar_com_data_no_passado_retorna_422(client):
    resposta = cria(client, data_hora=horario_futuro(dias=-1).isoformat())

    assert resposta.status_code == 422


def test_motivo_e_opcional(client):
    dados = payload()
    del dados["motivo"]

    resposta = client.post("/consultas", json=dados)

    assert resposta.status_code == 201
    assert resposta.json()["motivo"] is None


# ---------- conflito de horário ----------

def test_mesmo_profissional_no_mesmo_horario_retorna_409(client):
    horario = horario_futuro().isoformat()
    assert cria(client, data_hora=horario).status_code == 201

    resposta = cria(client, paciente_id="paciente-002", data_hora=horario)

    assert resposta.status_code == 409


def test_profissionais_diferentes_no_mesmo_horario_sao_permitidos(client):
    horario = horario_futuro().isoformat()
    assert cria(client, profissional_id="medico-001", data_hora=horario).status_code == 201

    resposta = cria(client, profissional_id="medico-002", data_hora=horario)

    assert resposta.status_code == 201


def test_horario_liberado_apos_cancelamento(client):
    horario = horario_futuro().isoformat()
    consulta = cria(client, data_hora=horario).json()
    client.post(f"/consultas/{consulta['id']}/cancelamento")

    resposta = cria(client, data_hora=horario)

    assert resposta.status_code == 201


# ---------- consulta por id e listagem ----------

def test_consultar_por_id_retorna_a_consulta(client):
    criada = cria(client).json()

    resposta = client.get(f"/consultas/{criada['id']}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == criada["id"]


def test_consultar_id_inexistente_retorna_404(client):
    resposta = client.get(f"/consultas/{uuid4()}")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Consulta não encontrada"


def test_consultar_id_malformado_retorna_422(client):
    resposta = client.get("/consultas/nao-e-um-uuid")

    assert resposta.status_code == 422


def test_listar_sem_consultas_retorna_lista_vazia(client):
    resposta = client.get("/consultas")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_listar_retorna_todas_as_consultas(client):
    cria(client, data_hora=horario_futuro(1).isoformat())
    cria(client, data_hora=horario_futuro(2).isoformat())

    resposta = client.get("/consultas")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 2


# ---------- cancelamento ----------

def test_cancelar_consulta_muda_status_para_cancelada(client):
    criada = cria(client).json()

    resposta = client.post(f"/consultas/{criada['id']}/cancelamento")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "cancelada"
    assert client.get(f"/consultas/{criada['id']}").json()["status"] == "cancelada"


def test_cancelar_consulta_inexistente_retorna_404(client):
    resposta = client.post(f"/consultas/{uuid4()}/cancelamento")

    assert resposta.status_code == 404


def test_cancelar_duas_vezes_retorna_409(client):
    criada = cria(client).json()
    client.post(f"/consultas/{criada['id']}/cancelamento")

    resposta = client.post(f"/consultas/{criada['id']}/cancelamento")

    assert resposta.status_code == 409


def test_health(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json()["service"] == "scheduling"