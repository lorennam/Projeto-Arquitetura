# Relatório Técnico: Middleware Distribuído para o Domínio de Saúde

Equipe: Arthur, Bento, Anna, Lucas e Lorenna.

## 1. Descrição da arquitetura

O sistema é um middleware distribuído para o domínio de saúde, em Python, executado com `docker compose`. O **gateway** (`middleware`) é implementado por nós, sem middleware pronto, e é o único componente exposto ao host.

![Diagrama de arquitetura](img/arquitetura.png)

| Componente | Papel |
| --- | --- |
| `middleware` (8000) | Gateway: roteamento, JWT, RBAC, correlation ID, timeout, retry, circuit breaker |
| `scheduling` (8001) | Agendamento de consultas; produtor de eventos; cliente gRPC |
| `medical-record` (8002) | Prontuário; servidor gRPC |
| `notification` (8003) | API de notificações e consumidor de eventos |
| `rabbitmq` | Broker de mensagens |
| `jaeger`, `prometheus`, `grafana` | Tracing, métricas e painéis |

**Fluxo síncrono:** cliente → gateway (valida JWT e papel) → serviço (REST).
**Fluxo assíncrono:** `scheduling` publica `consulta.agendada` → RabbitMQ → `notification` consome.
**Chamada interna:** `scheduling` → `medical-record` por gRPC, para consultar se o paciente tem prontuário.

Os serviços só se comunicam pela rede, nunca por import direto. Cada serviço tem seu próprio repositório de dados em memória.

## 2. Decisões técnicas e justificativas

### 2.1 Segurança (JWT e RBAC)

**Autenticação.** `POST /auth/login` valida usuários de teste (paciente, médico e admin) e emite um JWT (HS256) com `sub`, `role`, `iat` e `exp` (30 min). O segredo vem do `.env`, e o gateway **falha ao subir** se ele não existir, em vez de rodar com um valor padrão. A decodificação fixa `algorithms=[...]`, o que impede o ataque de troca de algoritmo no header do token.

**Validação no gateway.** Um middleware valida o token em toda requisição, exceto numa **allowlist** de rotas públicas (`/health`, `/metrics`, `/auth/login` e a documentação). Uma rota nova nasce protegida por padrão. Respostas `401` (sem token, expirado ou inválido) saem com `WWW-Authenticate: Bearer`.

**Autorização (RBAC).** Uma tabela serviço × papel × método define o que cada papel pode fazer; o que não está listado é **negado** (privilégio mínimo). Resposta `403` para papel sem permissão.

| Serviço | `patient` | `doctor` | `admin` |
| --- | --- | --- | --- |
| `scheduling` | GET, POST | todos | todos |
| `medical-record` | negado | todos | negado |
| `notification` | GET | GET | todos |

**Identidade para os serviços.** Após validar o token, o gateway repassa `X-User-Id` e `X-User-Role`. Como o proxy copia os headers do cliente, **todo `X-User-*` vindo de fora é descartado antes** de injetar os valores do token, o que impede a falsificação de identidade.

**Ordem dos middlewares.** Tracing → Correlation ID → JWT → RBAC. Assim, `401` e `403` também saem com `X-Correlation-ID` e aparecem no trace.

**Justificativas e trade-offs**

- `medical-record` só para médico: dado clínico sensível. Nem o admin acessa.
- `401` ("não sei quem é você") e `403` ("sei quem é, mas não pode") são distinguidos, e a mensagem de login inválido é a mesma para usuário inexistente e senha errada.
- Os serviços internos confiam nos headers `X-User-*` porque só o gateway é alcançável de fora.

**Limitações assumidas**

- Usuários em memória e hash SHA-256 sem salt: adequado só para teste; em produção, banco com bcrypt/argon2.
- Sem renovação (refresh) nem revogação de token.
- A chamada gRPC interna não passa pelo gateway, então JWT e RBAC não se aplicam; em produção, usar mTLS.
- Regra "paciente lê o próprio prontuário" não implementada (exigiria filtro por `X-User-Id` no serviço).
- Rotas de documentação públicas por conveniência de demo.

### 2.2 Gateway e resiliência
### 2.3 Mensageria e consistência
### 2.4 Serviços de negócio e contratos
### 2.5 Observabilidade e tracing
### 2.6 Comunicação interna via gRPC
### 2.7 Versionamento de API
### 2.8 Infraestrutura

## 3. Dificuldades e lições aprendidas

| Dificuldade | Lição |
| --- | --- |
| O proxy copiava todos os headers do cliente, abrindo espaço para forjar `X-User-Role` | Descartar o que vem de fora antes de injetar identidade |
| A ordem dos middlewares do Starlette (o último adicionado é o mais externo) determinava se `401` e `403` saíam com correlation ID | Documentar a ordem e testar com `curl -i` |
| O consumidor e o produtor do RabbitMQ em loop de reconexão: o produtor bloqueia a requisição quando o broker cai (cliente recebe `409` ou `504` com a consulta criada) | Testar cada queda; o próximo passo seria *transactional outbox* |
| O gateway repete `POST` sem idempotência | Idempotência precisa ser pensada junto com o retry |
| Conflitos de versões no tracing (`fastapi 0.115.6`, `setuptools<81`, `grpcio 1.62.3` por causa do `protobuf<5`) | Fixar versões testadas em conjunto |
| O contexto de build do Docker não enxergava o `proto/` na raiz | Mover o contexto para a raiz e usar `.dockerignore` para não copiar `.env` |
| Código gerado do protobuf não deve ir para o Git | Gerar no build e ignorar `*_pb2*.py` |
| Healthcheck `unhealthy` por rota `/health` perdida em um merge | O roteiro ponta a ponta achou o problema; testar após cada merge |
| Merges e conflitos em `requirements.txt` e `docker-compose.yml` entre PRs paralelos | Branches curtas, PRs pequenos e ordem de merge combinada |

## 4. Uso de IA/LLM

_(a completar)_