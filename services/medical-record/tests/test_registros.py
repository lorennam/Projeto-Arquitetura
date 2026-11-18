from uuid import uuid4

BASE = "/v1/pacientes"


def payload(**alteracoes):
    dados = {
        "profissional_id": "medico-001",
        "tipo": "exame",
        "descricao": "Hemograma completo sem alterações",
    }
    dados.update(alteracoes)
    return dados


def adiciona(client, paciente_id="paciente-001", **alteracoes):
    return client.post(f"{BASE}/{paciente_id}/registros", json=payload(**alteracoes))


# ---------- adição de registro ----------

def test_adicionar_registro_retorna_201(client):
    resposta = adiciona(client)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["paciente_id"] == "paciente-001"
    assert corpo["profissional_id"] == "medico-001"
    assert corpo["tipo"] == "exame"
    assert corpo["id"]
    assert corpo["criado_em"]


def test_consulta_id_e_opcional_e_armazenada(client):
    sem = adiciona(client)
    com = adiciona(client, consulta_id="consulta-123")

    assert sem.json()["consulta_id"] is None
    assert com.json()["consulta_id"] == "consulta-123"


def test_descricao_tem_espacos_removidos(client):
    resposta = adiciona(client, descricao="   Paciente estável   ")

    assert resposta.json()["descricao"] == "Paciente estável"


def test_descricao_vazia_retorna_422(client):
    assert adiciona(client, descricao="").status_code == 422
    assert adiciona(client, descricao="    ").status_code == 422


def test_descricao_acima_do_limite_retorna_422(client):
    assert adiciona(client, descricao="x" * 2001).status_code == 422


def test_descricao_no_limite_e_aceita(client):
    assert adiciona(client, descricao="x" * 2000).status_code == 201


def test_tipo_invalido_retorna_422(client):
    assert adiciona(client, tipo="desconhecido").status_code == 422


def test_campo_obrigatorio_ausente_retorna_422(client):
    dados = payload()
    del dados["profissional_id"]

    resposta = client.post(f"{BASE}/paciente-001/registros", json=dados)

    assert resposta.status_code == 422


# ---------- consulta do prontuário ----------

def test_prontuario_sem_registros_retorna_lista_vazia(client):
    resposta = client.get(f"{BASE}/paciente-001/registros")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_consultar_prontuario_retorna_registros_na_ordem_de_adicao(client):
    adiciona(client, descricao="primeiro")
    adiciona(client, descricao="segundo")

    resposta = client.get(f"{BASE}/paciente-001/registros")

    assert resposta.status_code == 200
    assert [r["descricao"] for r in resposta.json()] == ["primeiro", "segundo"]


def test_prontuarios_de_pacientes_sao_isolados(client):
    adiciona(client, paciente_id="paciente-001")
    adiciona(client, paciente_id="paciente-002")
    adiciona(client, paciente_id="paciente-002")

    assert len(client.get(f"{BASE}/paciente-001/registros").json()) == 1
    assert len(client.get(f"{BASE}/paciente-002/registros").json()) == 2


def test_filtro_por_tipo(client):
    adiciona(client, tipo="exame")
    adiciona(client, tipo="anotacao")
    adiciona(client, tipo="exame")

    exames = client.get(f"{BASE}/paciente-001/registros?tipo=exame").json()
    prescricoes = client.get(f"{BASE}/paciente-001/registros?tipo=prescricao").json()

    assert len(exames) == 2
    assert all(r["tipo"] == "exame" for r in exames)
    assert prescricoes == []


def test_filtro_com_tipo_invalido_retorna_422(client):
    resposta = client.get(f"{BASE}/paciente-001/registros?tipo=xyz")

    assert resposta.status_code == 422


# ---------- registro por id ----------

def test_consultar_registro_por_id(client):
    criado = adiciona(client).json()

    resposta = client.get(f"{BASE}/paciente-001/registros/{criado['id']}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == criado["id"]


def test_registro_inexistente_retorna_404(client):
    resposta = client.get(f"{BASE}/paciente-001/registros/{uuid4()}")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Registro não encontrado"


def test_registro_de_outro_paciente_retorna_404(client):
    criado = adiciona(client, paciente_id="paciente-001").json()

    resposta = client.get(f"{BASE}/paciente-002/registros/{criado['id']}")

    assert resposta.status_code == 404


def test_registro_com_id_malformado_retorna_422(client):
    resposta = client.get(f"{BASE}/paciente-001/registros/nao-e-um-uuid")

    assert resposta.status_code == 422


# ---------- versionamento e health ----------

def test_rotas_sem_prefixo_v1_nao_existem(client):
    assert client.get("/pacientes/paciente-001/registros").status_code == 404


def test_health_fica_fora_do_prefixo_v1(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json()["service"] == "medical-record"