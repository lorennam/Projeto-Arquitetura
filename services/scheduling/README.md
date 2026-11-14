# Scheduling Service

Serviço de agendamento de consultas (porta `8001`). Faz parte da rede interna do Docker: só o `middleware` (porta 8000) é exposto ao host.

O armazenamento é **em memória**, então os dados somem quando o container reinicia.

## Endpoints

| Método | Rota | Descrição | Respostas |
| --- | --- | --- | --- |
| `GET` | `/health` | Verifica se o serviço está de pé | `200` |
| `POST` | `/consultas` | Cria uma consulta (status inicial `agendada`) | `201`, `409`, `422` |
| `GET` | `/consultas` | Lista todas as consultas | `200` |
| `GET` | `/consultas/{id}` | Consulta uma consulta pelo id | `200`, `404`, `422` |
| `POST` | `/consultas/{id}/cancelamento` | Cancela uma consulta | `200`, `404`, `409`, `422` |

### Códigos de resposta

| Código | Quando acontece |
| --- | --- |
| `200` | Consulta encontrada, listada ou cancelada |
| `201` | Consulta criada |
| `404` | Consulta não encontrada. Corpo: `{"detail": "Consulta não encontrada"}` |
| `409` | Criação: o profissional já tem consulta agendada nesse horário. Cancelamento: a consulta já está cancelada |
| `422` | Dados inválidos: campo obrigatório ausente, id que não é UUID ou `data_hora` no passado |

Erros `404` e `409` seguem o formato `{"detail": "<mensagem>"}`. O `422` usa o formato padrão de validação do FastAPI.

### Regras de negócio

- `data_hora` deve estar no futuro. Sem fuso horário, é assumido UTC.
- Um profissional não pode ter duas consultas **agendadas** exatamente no mesmo horário.
- Cancelar não apaga a consulta: ela continua existindo com status `cancelada`, e o horário volta a ficar livre.

### Exemplo

Criar consulta (`POST /consultas`):

```json
{
  "paciente_id": "paciente-001",
  "profissional_id": "medico-001",
  "data_hora": "2030-05-20T14:30:00Z",
  "motivo": "Consulta de rotina"
}
```

Resposta `201`:

```json
{
  "paciente_id": "paciente-001",
  "profissional_id": "medico-001",
  "data_hora": "2030-05-20T14:30:00Z",
  "motivo": "Consulta de rotina",
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "agendada",
  "criado_em": "2026-11-13T20:58:00Z"
}
```

## Contrato OpenAPI

O contrato completo está em [`docs/openapi-scheduling.json`](../../docs/openapi-scheduling.json) e pode ser aberto em https://editor.swagger.io.

O arquivo é **gerado** a partir do código. Sempre que mudar rotas ou schemas, gere de novo, a partir de `services/scheduling/app`:

```bash
python -c "import json; from main import app; json.dump(app.openapi(), open('../../../docs/openapi-scheduling.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)"
```

## Testes

Da raiz do repositório:

```bash
pip install -r services/scheduling/requirements-dev.txt
python -m pytest services/scheduling/tests -q
```

## Estrutura

```
services/scheduling/
├── app/
│   ├── main.py         # rotas FastAPI
│   ├── schemas.py      # modelos de entrada e saída
│   ├── enums.py        # status da consulta
│   ├── erros.py        # modelo das respostas de erro
│   └── repository.py   # armazenamento em memória
├── tests/              # testes automatizados (pytest)
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```