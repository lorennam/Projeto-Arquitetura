from datetime import datetime, timedelta, timezone


def inicio_futuro(dias=7):
    return (datetime.now(timezone.utc) + timedelta(days=dias)).replace(microsecond=0)


def payload_v2(**alteracoes):
    dados = {
        "paciente_id": "paciente-001",
        "profissional_id": "medico-001",
        "inicio": inicio_futuro().isoformat(),
    }
    dados.update(alteracoes)
    return dados


def test_v2_cria_consulta_com_inicio(client):
    resposta = client.post("/v2/consultas", json=payload_v2())

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert "inicio" in corpo
    assert "data_hora" not in corpo
    assert corpo["status"] == "agendada"


def test_v2_com_data_no_passado_retorna_422(client):
    resposta = client.post(
        "/v2/consultas", json=payload_v2(inicio=inicio_futuro(-1).isoformat())
    )

    assert resposta.status_code == 422


def test_v2_conflito_de_horario_retorna_409(client):
    horario = inicio_futuro().isoformat()
    assert client.post("/v2/consultas", json=payload_v2(inicio=horario)).status_code == 201

    resposta = client.post("/v2/consultas", json=payload_v2(inicio=horario))

    assert resposta.status_code == 409


def test_v1_continua_funcionando_apos_v2(client):
    resposta = client.post(
        "/v1/consultas",
        json={
            "paciente_id": "paciente-001",
            "profissional_id": "medico-001",
            "data_hora": inicio_futuro().isoformat(),
        },
    )

    assert resposta.status_code == 201
    assert "data_hora" in resposta.json()