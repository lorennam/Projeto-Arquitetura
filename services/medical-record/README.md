# Medical Record Service

Serviço de prontuário médico (porta `8002`). Faz parte da rede interna do Docker: só o `middleware` (porta 8000) é exposto ao host. O controle de acesso por papel é feito no gateway, não neste serviço.

O armazenamento é **em memória**, então os dados somem quando o container reinicia.

## Endpoints

A API é versionada: todas as rotas de negócio ficam sob `/v1`. Apenas o `/health` fica fora do prefixo, por ser rota de infraestrutura.

| Método | Rota | Descrição | Respostas |
| --- | --- | --- | --- |
| `GET` | `/health` | Verifica se o serviço está de pé | `200` |
| `POST` | `/v1/pacientes/{paciente_id}/registros` | Adiciona um registro ao prontuário | `201`, `422` |
| `GET` | `/v1/pacientes/{paciente_id}/registros` | Consulta o prontuário (filtro opcional `?tipo=`) | `200`, `422` |
| `GET` | `/v1/pacientes/{paciente_id}/registros/{registro_id}` | Consulta um registro específico | `200`, `404`, `422` |

### Códigos de resposta

| Código | Quando acontece |
| --- | --- |
| `200` | Registro ou lista encontrados. Paciente sem registros recebe lista vazia |
| `201` | Registro adicionado |
| `404` | Registro não encontrado, ou pertencente a outro paciente. Corpo: `{"detail": "Registro não encontrado"}` |
| `422` | Dados inválidos: campo obrigatório ausente, `tipo` desconhecido, `descricao` vazia ou com mais de 2000 caracteres, ou id que não é UUID |

### Regras de negócio

- Tipos de registro aceitos: `anotacao`, `exame` e `prescricao`.
- A `descricao` tem os espaços das pontas removidos e não pode ficar vazia.
- Registros são **imutáveis**: o prontuário é um histórico, então não há edição nem exclusão.
- `consulta_id` é opcional e apenas armazenado, sem validação contra o `scheduling` (os serviços só se falam pela rede).
- O prontuário devolve os registros na ordem em que foram adicionados.

### Exemplo

Adicionar registro (`POST /v1/pacientes/paciente-001/registros`):

```json
{
  "profissional_id": "medico-001",
  "tipo": "exame",
  "descricao": "Hemograma completo sem alterações",
  "consulta_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

Resposta `201`:

```json
{
  "profissional_id": "medico-001",
  "tipo": "exame",
  "descricao": "Hemograma completo sem alterações",
  "consulta_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "id": "9b2f6d1e-4c3a-4f5b-8a7d-1e2f3a4b5c6d",
  "paciente_id": "paciente-001",
  "criado_em": "2026-11-15T21:34:00Z"
}
```

## Contrato OpenAPI

O contrato completo está em [`docs/openapi-medical-record.json`](../../docs/openapi-medical-record.json) e pode ser aberto em https://editor.swagger.io.

O arquivo é **gerado** a partir do código. Sempre que mudar rotas ou schemas, gere de novo, a partir de `services/medical-record/app`:

```bash
python -c "import json; from main import app; json.dump(app.openapi(), open('../../../docs/openapi-medical-record.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)"
```

## Testes

Da raiz do repositório:

```bash
pip install -r services/medical-record/requirements-dev.txt
python -m pytest services/medical-record/tests -q
```

## Estrutura

```
services/medical-record/
├── app/
│   ├── main.py         # rotas FastAPI (APIRouter /v1)
│   ├── schemas.py      # modelos de entrada e saída
│   ├── enums.py        # tipos de registro
│   ├── erros.py        # modelo das respostas de erro
│   └── repository.py   # armazenamento em memória
├── tests/              # testes automatizados (pytest)
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```