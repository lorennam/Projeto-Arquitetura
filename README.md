<h1 align="center">
  Middleware Distribuído para Saúde
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white" alt="RabbitMQ" />
  <img src="https://img.shields.io/badge/gRPC-244C5A?style=for-the-badge&logo=grpc&logoColor=white" alt="gRPC" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white" alt="JWT" />
  <img src="https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white" alt="Prometheus" />
  <img src="https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white" alt="Grafana" />
  <img src="https://img.shields.io/badge/Jaeger-66CFE3?style=for-the-badge&logo=jaeger&logoColor=black" alt="Jaeger" />
</p>

<p align="center">
  Gateway próprio com autenticação, autorização, resiliência e observabilidade, conectando serviços de agendamento, prontuário, notificação e cadastro de pacientes.
</p>

---

## Sobre o projeto

Projeto da disciplina **Arquitetura de Sistemas**. O objetivo é construir, do zero, um **middleware distribuído** que conecte serviços de uma aplicação real. Escolhemos o domínio de **Saúde**.

O middleware (`middleware/`) é um gateway implementado por nós, sem Kong, Istio ou outra ferramenta pronta. Ele é o único componente exposto ao host e concentra roteamento, JWT, RBAC, correlation ID, timeout, retry com backoff e circuit breaker. Os serviços de negócio têm lógica simplificada: o foco é a comunicação entre eles.

### Equipe

| Integrante | Responsabilidade |
| --- | --- |
| Arthur | Infraestrutura, Docker, Prometheus e Grafana |
| Bento | Segurança: JWT, validação no gateway e RBAC |
| Anna | Gateway e resiliência (timeout, retry, circuit breaker) |
| Lucas | Mensageria (RabbitMQ: produtor, consumidor, retry, DLQ, idempotência) |
| Lorenna | Serviços de negócio e contratos de API |

### Domínio: Saúde

| Serviço | Função |
| --- | --- |
| `scheduling` | Agendamento de consultas |
| `medical-record` | Prontuário do paciente |
| `notification` | Notificação de consultas agendadas (API + consumidor de eventos) |
| `patient-extra-point` | Cadastro de pacientes (CRUD, PostgreSQL) |

---

## Arquitetura

![Diagrama de arquitetura](docs/img/arquitetura.png)

| Componente | Porta | Papel |
| --- | --- | --- |
| `middleware` | `8000` (**único exposto ao host**) | Gateway: roteamento `/api/<serviço>/<versão>/...`, JWT, RBAC, correlation ID, timeout, retry e circuit breaker |
| `scheduling` | `8001` (interna) | Consultas (`v1` e `v2`); publica `consulta.agendada` no RabbitMQ; cliente gRPC |
| `medical-record` | `8002` REST, `50051` gRPC (internas) | Prontuário; servidor gRPC; só o papel `doctor` acessa |
| `notification` | `8003` (interna) | API de notificações |
| `notification-consumer` | sem porta | Worker que consome a fila, com retry, DLQ e idempotência |
| `patient-extra-point` | `8004` (interna) | Cadastro de pacientes; persistência em PostgreSQL |
| `patient-db` | `5432` (interna) | PostgreSQL do `patient-extra-point` |
| `rabbitmq` | `15672` (painel, só localhost) | Broker de mensagens (vhost `health`) |
| `prometheus` | `9090` (só localhost) | Coleta de métricas |
| `grafana` | `3000` (só localhost) | Dashboard de métricas |
| `jaeger` | `16686` (só localhost) | Tracing distribuído |

**Fluxo síncrono:** cliente → gateway (valida JWT e papel) → serviço (REST).
**Fluxo assíncrono:** `scheduling` publica `consulta.agendada` → RabbitMQ → `notification-consumer`.
**Chamada interna:** `scheduling` → `medical-record` por gRPC (`ExisteProntuario`).

Os serviços só se comunicam pela rede, e apenas o gateway é alcançável de fora (os demais ficam na rede interna do Docker).

---

## Como rodar

**Pré-requisitos:** Docker e Docker Compose. Os comandos abaixo são para PowerShell, na raiz do repositório.

### 1. Clonar e configurar o `.env`

```powershell
git clone <url-do-repositorio>
cd Projeto-Arquitetura
Copy-Item .env.example .env
```

Edite o `.env` e defina os valores. As variáveis principais:

| Variável | Uso |
| --- | --- |
| `JWT_SECRET` | Segredo do JWT. **Obrigatória:** o gateway não sobe sem ela |
| `PATIENT_PASSWORD`, `DOCTOR_PASSWORD`, `ADMIN_PASSWORD` | Senhas dos usuários de teste |
| `GRAFANA_USER`, `GRAFANA_PASSWORD` | Acesso ao Grafana |
| Credenciais do RabbitMQ e do PostgreSQL | Veja `.env.example` para a lista completa |

O `.env` não vai para o Git; o `.env.example` é versionado.

### 2. Subir tudo

```powershell
docker compose up --build -d
docker compose ps
```

O primeiro build pode levar alguns minutos. Quando terminar, todos os containers devem estar `healthy` (o `notification-consumer` não tem healthcheck e só precisa estar `Up`).

### 3. Parar

```powershell
docker compose down
```

Os dados de `scheduling` e `medical-record` ficam em memória e são perdidos ao reiniciar o container.

---

## Usuários de teste

| Usuário | Senha | Papel |
| --- | --- | --- |
| `paciente` | `paciente123` | `patient` |
| `medico` | `medico123` | `doctor` |
| `admin` | `admin123` | `admin` |

Esses são os valores padrão; se o `.env` definir outras senhas, valem as do `.env`.

**Login (PowerShell):**

```powershell
$t = (Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login `
  -ContentType "application/json" `
  -Body '{"username":"medico","password":"medico123"}').access_token
$h = @{ Authorization = "Bearer $t" }
```

**Login (Linux/macOS/Git Bash):**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"medico","password":"medico123"}'
```

Resposta: `{"access_token": "<jwt>", "token_type": "bearer", "expires_in": 1800}`. O token vale 30 minutos.

---

## Endpoints e URLs úteis

### URLs

| O quê | URL |
| --- | --- |
| Gateway (único exposto) | http://localhost:8000 |
| Swagger do gateway | http://localhost:8000/docs |
| Painel do RabbitMQ (vhost `health`) | http://localhost:15672 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Jaeger | http://localhost:16686 |

O login do RabbitMQ e do Grafana vem do `.env`.

### Endpoints principais (todos via gateway, com `Authorization: Bearer <token>`)

| Serviço | Método e rota | Descrição |
| --- | --- | --- |
| gateway | `POST /auth/login` | Emite o JWT (público) |
| `scheduling` | `POST /api/scheduling/v1/consultas` | Cria consulta (campo `data_hora`) |
| `scheduling` | `POST /api/scheduling/v2/consultas` | Cria consulta (campo `inicio`) |
| `scheduling` | `GET /api/scheduling/v1/consultas` | Lista consultas |
| `scheduling` | `GET /api/scheduling/v1/consultas/{id}` | Consulta por id |
| `scheduling` | `POST /api/scheduling/v1/consultas/{id}/cancelamento` | Cancela consulta |
| `medical-record` | `POST` e `GET /api/medical-record/v1/pacientes/{id}/registros` | Registros do prontuário (só `doctor`) |
| `patient-extra-point` | `GET`, `POST /api/patient-extra-point/v1/pacientes` | Lista e cadastra pacientes |
| `patient-extra-point` | `GET`, `PUT`, `DELETE /api/patient-extra-point/v1/pacientes/{id}` | Consulta, atualiza e exclui paciente |

Os contratos detalhados (payloads e códigos de resposta) estão em `docs/openapi-scheduling.json` e no `/docs` de cada serviço (rede interna).

**Exemplo: agendar uma consulta**

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/scheduling/v1/consultas `
  -Headers $h -ContentType "application/json" `
  -Body '{"paciente_id":"paciente-001","profissional_id":"medico-001","data_hora":"2030-05-20T14:30:00Z"}'
```

**Exemplo: cadastrar um paciente (admin)**

```powershell
$a = (Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}').access_token
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/patient-extra-point/v1/pacientes `
  -Headers @{ Authorization = "Bearer $a" } -ContentType "application/json" `
  -Body '{"nome":"Paciente Teste","cpf":"12345678901","data_nascimento":"1990-05-20"}'
```

---

## Como executar a demo

A demo ao vivo tem cerca de 5 minutos e percorre: subir a stack, acessos negados (401/403), fluxo completo (agendar, fila, notificação, prontuário), correlation ID e trace no Jaeger, queda de um serviço com circuit breaker e Grafana.

### Antes de começar

```powershell
docker compose up --build -d
docker compose ps
docker compose exec rabbitmq rabbitmqctl purge_queue -p health notification.consultas.dlq
```

1. Confirme que todos os containers estão `healthy`.
2. No Grafana, importe o dashboard uma vez: **Dashboards → New → Import**, envie `docs/grafana-dashboard.json` e escolha o Prometheus como fonte de dados. O dashboard se chama **Middleware Saude - Visao Geral**.
3. Gere alguns dados para os painéis não ficarem vazios: `1..15 | ForEach-Object { curl.exe -s "http://localhost:8000/test/latency?delay=$($_ % 4)" | Out-Null }`.

### Rodar a demo guiada

```powershell
powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
```

O script pausa entre as etapas (Enter para continuar):

| Etapa | O que mostra |
| --- | --- |
| 1 | `docker compose up -d` e `docker compose ps` |
| 2 | Login e acessos `401` (sem token), `403` (papel sem permissão) e `200` |
| 3 | Fluxo completo: prontuário, agendamento, evento na fila (1 mensagem), consumo (0 mensagens) |
| 4 | Correlation ID e trace no Jaeger (Service `middleware` → Find Traces) |
| 5 | Queda do `scheduling`: `504` nas 3 primeiras chamadas (~11,6 s), `503` imediato com `Retry-After: 10`, recuperação (`200`) |
| 6 | Dashboard do Grafana, com os picos de erro da queda |

O roteiro completo (tempos, falas, plano B e perguntas) está em [`docs/roteiro-demo.md`](docs/roteiro-demo.md).

### Teste ponta a ponta automatizado

```powershell
powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1
```

Executa 17 passos (login, prontuário, agendamento, evento na fila, notificação consumida, `401`/`403` e rastreio do correlation ID nos 4 containers) e imprime `[OK]` ou `[FALHOU]` por passo. O roteiro manual está em [`docs/roteiro-teste.md`](docs/roteiro-teste.md).

---

## Autenticação

O login é feito no gateway (`middleware`) e retorna um JWT (HS256) com `sub` (usuário), `role` (papel), `iat` e `exp`. Credenciais inválidas retornam `401`. A mensagem é a mesma para usuário inexistente e senha errada.

### Validação do token no gateway

Todas as rotas exigem `Authorization: Bearer <token>`, exceto as rotas públicas. A lista é uma allowlist: uma rota nova nasce protegida por padrão.

| Rota pública | Motivo |
| --- | --- |
| `/health` | Healthcheck |
| `/metrics` | Scrape do Prometheus |
| `/auth/login` | Emissão do token |
| `/test/latency` | Rota de teste que gera latência conhecida para o dashboard do Grafana (sem acesso a dados) |
| `/docs`, `/redoc`, `/openapi.json` | Documentação interativa (apenas desenvolvimento/demo) |

Respostas `401` (com `WWW-Authenticate: Bearer`):

| Situação | Mensagem |
| --- | --- |
| Header `Authorization` ausente ou fora do formato `Bearer <token>` | `Token de autenticação ausente` |
| Token expirado | `Token expirado` |
| Assinatura inválida, token malformado ou sem `sub`/`role` | `Token inválido` |

### Identidade repassada aos serviços

Depois de validar o token, o gateway repassa a identidade por headers:

| Header | Conteúdo |
| --- | --- |
| `X-User-Id` | Usuário (claim `sub`) |
| `X-User-Role` | Papel (claim `role`: `patient`, `doctor` ou `admin`) |

Qualquer header `X-User-*` enviado pelo cliente é descartado pelo gateway antes de repassar a requisição, para impedir que alguém forje a identidade. Os serviços confiam nesses headers porque só o gateway é alcançável de fora.

### Autorização por papéis (RBAC)

O gateway confere se o papel pode usar o método HTTP no serviço pedido. A tabela é uma allowlist: o que não está listado é **negado** (privilégio mínimo).

| Serviço (`/api/<serviço>/...`) | `patient` | `doctor` | `admin` |
| --- | --- | --- | --- |
| `scheduling` | GET, POST | todos os métodos | todos os métodos |
| `medical-record` | negado | todos os métodos | negado |
| `notification` | GET | GET | todos os métodos |
| `patient-extra-point` | GET | negado | todos os métodos |

**Decisões e limitações:**

- O `medical-record` é acessível **apenas por médico**: é dado clínico sensível, e nem o admin acessa.
- Respostas: `401` (sem token, expirado ou inválido) e `403` (autenticado, mas sem permissão).
- A regra "paciente vê só o próprio prontuário/cadastro" não foi implementada: exigiria filtrar por `X-User-Id` no serviço. Hoje, um `patient` com `GET` no `patient-extra-point` lista todos os cadastros. Fica como evolução (LGPD).

A tabela fica em `middleware/app/auth/permissions.py`.

---

## Resiliência e tolerância a falhas

O gateway aplica timeout, retry com backoff exponencial e circuit breaker **por serviço**, configuráveis por variáveis de ambiente:

| Mecanismo | Padrão | Variável |
| --- | --- | --- |
| Timeout por tentativa | 5 s | `GATEWAY_TIMEOUT_SECONDS` |
| Timeout de conexão | 2 s | `GATEWAY_CONNECT_TIMEOUT_SECONDS` |
| Retries | 3 (backoff 0,5 s, 1 s, 2 s) | `GATEWAY_MAX_RETRIES`, `GATEWAY_BACKOFF_BASE_SECONDS` |
| Falhas para abrir o breaker | 3 | `GATEWAY_CB_FAILURE_THRESHOLD` |
| Tempo até tentar recuperar (half-open) | 10 s | `GATEWAY_CB_RECOVERY_SECONDS` |

| Situação | Resposta do gateway |
| --- | --- |
| Serviço parado (timeouts em todas as tentativas) | `504` após ~11,6 s |
| Breaker aberto | `503` imediato, com `Retry-After: 10` |
| Serviço inexistente | `404` |

Só falhas de rede são repetidas; respostas HTTP `4xx` e `5xx` do serviço são repassadas ao cliente.

**Modelo de consistência:** eventual entre serviços (evento `consulta.agendada` via RabbitMQ) e forte dentro de cada serviço. A estratégia completa, o comportamento na queda de cada componente e as limitações conhecidas estão em [`docs/tolerancia-falhas.md`](docs/tolerancia-falhas.md).

---

## Mensageria (RabbitMQ)

- **Produtor:** `scheduling` publica `consulta.agendada` na exchange `health.events` (topic).
- **Consumidor:** `notification-consumer` lê a fila `notification.consultas` com `ack` manual.
- **Entrega:** mensagens persistentes, filas duráveis e confirmação de publicação (*at-least-once*).
- **Retry e DLQ:** falhas voltam por uma fila de retry (TTL de 5 s, até 3 vezes) e depois seguem para `notification.consultas.dlq`.
- **Idempotência:** o consumidor registra o `message_id` em SQLite (volume `notification_data`) e ignora duplicatas.

### Roteiro de testes manuais

Para validar a mensageria na prática (publicação, consumo, retry, DLQ, idempotência e reconexão), há um roteiro passo a passo em [`docs/relatorio_testes_rabbitmq.md`](docs/relatorio_testes_rabbitmq.md). Ele cobre as issues #12, #13, #14 e #27, com os comandos prontos para Git Bash e o resultado esperado de cada etapa.

---

## Observabilidade

Os serviços escrevem logs JSON (um por requisição, com `correlation_id`) e expõem métricas Prometheus em `GET /metrics`. O `X-Correlation-ID` é gerado no gateway, repassado por HTTP e gRPC e devolvido na resposta, inclusive em `401` e `403`.

| Serviço | Métricas |
| --- | --- |
| `middleware` | `http://localhost:8000/metrics` |
| `scheduling`, `medical-record`, `notification`, `patient-extra-point` | Só na rede interna (`<serviço>:<porta>/metrics`), coletadas pelo Prometheus |

O nível de log vem de `LOG_LEVEL` (padrão `INFO`). Detalhes em [`docs/observabilidade.md`](docs/observabilidade.md).

### Dashboard (Grafana)

O arquivo `docs/grafana-dashboard.json` traz o dashboard **Middleware Saude - Visao Geral** (requisições por segundo, latência p95, erros 5xx e requisições por status). Para importar: **Dashboards → New → Import**, escolher o arquivo e selecionar o Prometheus.

### Tracing distribuído (Jaeger + OpenTelemetry)

Uma requisição que passa pelo gateway e chega aos serviços aparece como **um único trace**.

![Trace da criação de consulta no Jaeger](docs/img/trace-jaeger.png)

*Criação de consulta: `middleware` → `scheduling` → `medical-record` (3 serviços, 13 spans).*

- Cada serviço instrumentado tem um `tracing.py` com `service.name` próprio e exporta spans por OTLP/HTTP para o Jaeger (`OTEL_EXPORTER_OTLP_ENDPOINT`, padrão `http://jaeger:4318`).
- **HTTP:** o gateway cria o trace e repassa o header W3C `traceparent`. Cada tentativa do retry vira um span de cliente.
- **gRPC:** o `scheduling` injeta o `traceparent` na metadata e o `medical-record` continua o trace.
- Respostas `401` e `403` também aparecem no trace (o tracing é o middleware mais externo).
- `/health` e `/metrics` ficam fora dos traces.
- **Cobertura:** `middleware`, `scheduling` e `medical-record` exportam traces. O `patient-extra-point` e o consumidor ainda não; a propagação por RabbitMQ não foi implementada.

**Como gerar um trace de exemplo:** crie um prontuário e uma consulta (veja a seção da demo) e, no Jaeger, escolha o serviço `middleware`, clique em **Find Traces** e abra o trace `POST /api/{service}/{path}` com 3 serviços.

**Versões fixadas (lições aprendidas):**

| Pacote | Versão | Motivo |
| --- | --- | --- |
| `fastapi` | `0.115.6` | O `opentelemetry-instrumentation-fastapi` 0.48b0 quebra com FastAPI mais novo em rotas de `include_router` |
| `setuptools` | `<81` | A instrumentação OTel ainda importa `pkg_resources` |
| `grpcio`, `grpcio-tools` | `1.62.3` | O `opentelemetry-proto` 1.27 exige `protobuf<5` |
| `opentelemetry-*` | `1.27.0` / `0.48b0` | Conjunto de versões testado em conjunto |

---

## Comunicação interna via gRPC

O `scheduling` consulta o `medical-record` por gRPC (`ExisteProntuario`) ao criar uma consulta.

- **Contrato:** `proto/prontuario.proto` (única fonte da verdade).
- **Geração de código:** no build de cada container (`grpc_tools.protoc`), sem versionar os `*_pb2.py`.
- **Servidor:** `medical-record`, porta `50051`, só na rede interna.
- **Cliente:** `scheduling`, com `MEDICAL_RECORD_GRPC_ADDR` (padrão `medical-record:50051`) e `GRPC_TIMEOUT_SECONDS` (padrão `2`).
- **Rastreabilidade:** o `X-Correlation-ID` viaja como metadata (`x-correlation-id`).
- **Tolerância a falhas:** a chamada é informativa; se o `medical-record` estiver fora do ar ou lento, o `scheduling` registra o aviso e segue com o agendamento.

---

## Versionamento da API

As rotas de negócio são versionadas no caminho, **depois do nome do serviço**: `/api/<serviço>/<versão>/...`. O gateway repassa o caminho sem alterá-lo, então o RBAC vale para todas as versões. Rotas de infraestrutura (`/health`, `/metrics`) não são versionadas.

| Serviço | Versões |
| --- | --- |
| `scheduling` | `v1`, `v2` (a `v2` troca o campo `data_hora` por `inicio`) |
| `medical-record` | `v1` |
| `patient-extra-point` | `v1` |

**v1**

```json
{"paciente_id": "paciente-001", "profissional_id": "medico-001", "data_hora": "2030-05-20T14:30:00Z"}
```

**v2**

```json
{"paciente_id": "paciente-001", "profissional_id": "medico-001", "inicio": "2030-05-20T14:30:00Z"}
```

A `v1` continua funcionando, e uma versão inexistente (por exemplo `v3`) responde `404`. As rotas sem versão (`/consultas`) deixaram de existir ao introduzir o `/v1`.

---

## Estrutura do repositório

| Pasta/arquivo | Conteúdo |
| --- | --- |
| `middleware/` | Gateway: roteamento, JWT, RBAC, resiliência, observabilidade |
| `services/` | Código de cada microsserviço (`scheduling`, `medical-record`, `notification`, `patient_extra_point`) |
| `proto/` | Contrato gRPC (`prontuario.proto`) |
| `docs/` | Relatório, diagramas, tolerância a falhas, observabilidade, roteiros e dashboard do Grafana |
| `scripts/` | `e2e.ps1` (teste ponta a ponta) e `demo.ps1` (demo guiada) |
| `docker-compose.yml` | Orquestração de todo o ambiente |

## Documentação

- [`docs/relatorio.md`](docs/relatorio.md): relatório técnico (arquitetura, decisões, lições e uso de IA)
- [`docs/tolerancia-falhas.md`](docs/tolerancia-falhas.md): estratégia de consistência e comportamento em falhas
- [`docs/observabilidade.md`](docs/observabilidade.md): logs, métricas e correlation ID
- [`docs/roteiro-demo.md`](docs/roteiro-demo.md): roteiro da demo ao vivo
- [`docs/roteiro-teste.md`](docs/roteiro-teste.md): roteiro de teste ponta a ponta
- [`docs/uso-ia.md`](docs/uso-ia.md): registro do uso de IA/LLM
- [`docs/relatorio_testes_rabbitmq.md`](docs/relatorio_testes_rabbitmq.md): roteiro de testes manuais do RabbitMQ (produtor, consumidor, retry, DLQ, idempotência e reconexão)

## Limitações conhecidas

- Usuários de teste em memória e hash SHA-256 sem salt (adequado só para teste).
- `scheduling` e `medical-record` guardam dados em memória.
- Com o RabbitMQ fora, `POST /consultas` pode responder `409` ou `504` mesmo com a consulta criada (o produtor tenta reconectar dentro da requisição).
- O retry do gateway também se aplica a `POST`, sem chave de idempotência.
- O gateway não é replicado (ponto único de falha) e a chamada gRPC interna não usa TLS.
- Um `patient` autenticado pode listar todos os pacientes no `patient-extra-point`.

Detalhes e o plano de evolução em [`docs/tolerancia-falhas.md`](docs/tolerancia-falhas.md).