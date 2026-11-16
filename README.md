# Projeto-Arquitetura


##  Ports

> por enquanto eu já temos as seguitnes portas para os seguintes serviços/containers

> port 8000 para o middleware          
> port 8001 para o schedlling                         
> port 8002 para medical-record                                     
> port 8003 para notification                 


para o serviço de mensagemria to usando o rabbit
para acessar ele online http://localhost:15672
ele vai ser utilizado para a comunicação entre os serviços

pipeline de como rodar o tem ate o momento

da clone
abre a pasta Projeto_Arquetetura
dentro dela mesmo manda um

## Autenticação

O login é feito no gateway (`middleware`) e retorna um JWT com o usuário e o papel.

**Usuários de teste:**

| Usuário | Senha | Papel |
| --- | --- | --- |
| `paciente` | `paciente123` | `patient` |
| `medico` | `medico123` | `doctor` |
| `admin` | `admin123` | `admin` |

**Login (Linux/macOS/Git Bash):**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"medico","password":"medico123"}'
```

**Login (PowerShell):**

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login `
  -ContentType "application/json" `
  -Body '{"username":"medico","password":"medico123"}'
```

**Resposta:**

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

O token contém os campos `sub` (usuário), `role` (papel), `iat` e `exp`.
Credenciais inválidas retornam `401`. A documentação interativa fica em `http://localhost:8000/docs`.

### Validação do token no gateway

Todas as rotas exigem um JWT válido no header `Authorization: Bearer <token>`, exceto as rotas públicas abaixo. A lista é uma allowlist: uma rota nova nasce protegida por padrão.

| Rota pública | Motivo |
| --- | --- |
| `/health` | Healthcheck |
| `/metrics` | Scrape do Prometheus |
| `/auth/login` | Emissão do token |
| `/docs`, `/redoc`, `/openapi.json` | Documentação interativa (apenas desenvolvimento/demo) |

Requisições às demais rotas respondem `401` com o header `WWW-Authenticate: Bearer` nos casos:

| Situação | Mensagem |
| --- | --- |
| Header `Authorization` ausente ou fora do formato `Bearer <token>` | `Token de autenticação ausente` |
| Token expirado | `Token expirado` |
| Assinatura inválida, token malformado ou sem `sub`/`role` | `Token inválido` |

**Exemplo:**

```powershell
$r = Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login `
  -ContentType "application/json" `
  -Body '{"username":"medico","password":"medico123"}'

Invoke-RestMethod http://localhost:8000/api/scheduling/health `
  -Headers @{ Authorization = "Bearer $($r.access_token)" }
```

### Identidade repassada aos serviços

Depois de validar o token, o gateway repassa a identidade aos serviços internos por headers:

| Header | Conteúdo |
| --- | --- |
| `X-User-Id` | Usuário (claim `sub`) |
| `X-User-Role` | Papel (claim `role`: `patient`, `doctor` ou `admin`) |

Qualquer header `X-User-*` enviado pelo cliente é descartado pelo gateway antes de repassar a requisição, para impedir que alguém forje a identidade. Os serviços internos confiam nesses headers porque só o gateway é alcançável de fora (os demais ficam na rede interna do Docker).

### Autorização por papéis (RBAC)

Depois de validar o token, o gateway confere se o papel do usuário (`role` do JWT) pode usar o método HTTP no serviço pedido. A tabela é uma allowlist: o que não está listado é **negado** (privilégio mínimo).

| Serviço (`/api/<serviço>/...`) | `patient` | `doctor` | `admin` |
| --- | --- | --- | --- |
| `scheduling` | GET, POST | todos os métodos | todos os métodos |
| `medical-record` | negado | todos os métodos | negado |
| `notification` | GET | GET | todos os métodos |

Métodos considerados: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.

**Decisões:**

- O `medical-record` é acessível **apenas por médico**. Por ser dado clínico sensível, nem o admin acessa (privilégio mínimo).
- Rotas fora de `/api/` (`/health`, `/auth/login`, docs) não passam pela tabela: são públicas ou protegidas apenas pelo JWT.
- A regra "paciente lê apenas o próprio prontuário" não foi implementada no gateway, pois exigiria que o serviço filtrasse os registros por `X-User-Id`. Fica como evolução.

**Respostas:**

| Situação | Código |
| --- | --- |
| Sem token, expirado ou inválido | `401` |
| Autenticado, mas papel sem permissão | `403` |

A tabela fica em `middleware/app/auth/permissions.py`; para mudar uma permissão basta editar esse dicionário.

## Observabilidade

Todos os serviços escrevem logs JSON (um por requisição, com `correlation_id`) e expõem métricas Prometheus em `GET /metrics`:

| Serviço | Métricas |
| --- | --- |
| middleware | `http://localhost:8000/metrics` |
| scheduling | `http://localhost:8001/metrics` |
| medical-record | `http://localhost:8002/metrics` |
| notification | `http://localhost:8003/metrics` |

O `X-Correlation-ID` é gerado no gateway, repassado aos serviços e devolvido na resposta. O nível de log vem da variável `LOG_LEVEL` (padrão `INFO`).

Detalhes em [`docs/observabilidade.md`](docs/observabilidade.md).

```
docker compose up --build -d
```

e basicamente ja vai estar rodando em segundo plano


deve aparecer algo nessa pegada no docker ps -a

```
❯ docker ps -a
CONTAINER ID   IMAGE                   COMMAND                  CREATED          STATUS                   PORTS                                                                                        NAMES
64e7aa55ad34   rabbitmq:3-management   "docker-entrypoint.s…"   21 minutes ago   Up 21 minutes            4369/tcp, 5671-5672/tcp, 15671/tcp, 15691-15692/tcp, 25672/tcp, 127.0.0.1:15672->15672/tcp   projeto-arquitetura-rabbitmq-1
7c3e0738d9e8   health-middleware       "uvicorn main:app --…"   21 minutes ago   Up 21 minutes            0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp                                                  projeto-arquitetura-middleware-1
fff5f4d8642c   health-medical-record   "uvicorn main:app --…"   21 minutes ago   Up 21 minutes            8002/tcp                                                                                     projeto-arquitetura-medical-record-1
db6463db0ce5   health-notification     "uvicorn main:app --…"   21 minutes ago   Up 21 minutes            8003/tcp                                                                                     projeto-arquitetura-notification-1
2a32b708bf19   health-scheduling       "uvicorn main:app --…"   21 minutes ago   Up 21 minutes            8001/tcp                                                                                     projeto-arquitetura-scheduling-1
```
