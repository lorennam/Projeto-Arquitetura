# Registro de uso de IA/LLM

Este documento registra onde e como o grupo usou IA/LLM no projeto. A responsabilidade técnica é do grupo: tudo que foi gerado com apoio de IA foi revisado e validado por quem o usou.

## Bento (segurança, bônus e documentação)

**Ferramenta/modelo:** Claude

### 1. Organização do projeto (`docs/divisao.md`, issues e `criar-issues.sh`)

- **Onde foi usada:** divisão das responsabilidades do grupo, lista de issues iniciais e script `criar-issues.sh` com o GitHub CLI.
- **Prompt principal:** enviei o enunciado do projeto e o README do Docker e pedi ajuda para dividir as tarefas entre 5 integrantes (Python, domínio Saúde), usando issues e uma branch por tarefa.

### 2. Login e emissão de JWT (#15, `feat/jwt-auth`)

- **Onde foi usada:** `POST /auth/login`, decisões de design (claims, usuários de teste, variáveis no `.env`), pacote `middleware/app/auth/`, `.gitignore`, `.env.example`, divisão em 10 commits, README e descrição do PR.
- **Prompts principais:** enviei o texto da issue e perguntei por onde começar; perguntei o que pedir ao Arthur para o `docker-compose.yml`, o que ir no `.gitignore` e `.env` vs `.env.local`; pedi para dividir a issue no máximo de commits e conduzir um por vez; enviei a estrutura real do `middleware`, o `Dockerfile` e o `main.py`; enviei erros do Docker e logs de build.
- **O que fiz/validei:** criei arquivos e commits, subi o container e testei o login (válido, senha errada com `401`, payload do JWT).

### 3. Validação do JWT no gateway (#16, `feat/jwt-validation`)

- **Onde foi usada:** middleware de validação, allowlist de rotas públicas, extração do token Bearer, headers internos `X-User-Id`/`X-User-Role` e proteção contra falsificação desses headers.
- **Prompts principais:** enviei a issue; enviei `main.py`, `gateway/router.py`, `correlation.py` e `config.py` da Anna para a IA encaixar o código; enviei as saídas dos testes (`401`, token inválido, `X-Correlation-ID`).
- **O que fiz/validei:** editei o `router.py` da Anna, testei sem token, token inválido e válido, e conferi o correlation ID no `401`.

### 4. Autorização por papéis (#17, `feat/rbac`)

- **Onde foi usada:** tabela serviço × papel × método, middleware que responde `403`, ordem dos middlewares e README.
- **Prompts principais:** enviei a issue pedindo ajuda; enviei o resultado dos testes com os três papéis; relatei que o script de teste colado não funcionava e pedi correção.
- **O que fiz/validei:** testei paciente, médico e admin em `medical-record`, `scheduling` e `notification`, e `401` sem token.

### 5. Tolerância a falhas e consistência (#18, `docs/tolerancia-falhas.md`)

- **Onde foi usada:** estrutura do documento, leitura de `circuit_breaker.py` e `consumer.py` para descrever o comportamento real, roteiro de testes de queda e redação.
- **Prompts principais:** enviei `circuit_breaker.py`, `observabilidade.md` e `consumer.py`; enviei os resultados dos testes com `scheduling`, `rabbitmq` e `medical-record` parados.
- **O que fiz/validei:** executei cada queda. O teste mostrou que o timeout é por tentativa (504 em ~11,6 s, depois 503 imediato) e que, com o RabbitMQ parado, a consulta é gravada mas o cliente recebe `409`. O documento foi corrigido com os valores medidos, não com os previstos.

### 6. Bônus: gRPC (`feat/grpc`)

- **Onde foi usada:** contrato `proto/prontuario.proto`, servidor no `medical-record`, cliente no `scheduling`, geração de código no build, `.dockerignore`, propagação do correlation ID por metadata e README.
- **Prompts principais:** perguntei se o bônus era viável; enviei Dockerfiles, `requirements.txt`, `main.py` e `docker-compose.yml`; enviei conflitos de merge e logs de build.
- **O que fiz/validei:** resolvi os conflitos em `requirements.txt`, rodei o teste de falha (`medical-record` parado, consulta criada) e confirmei o mesmo `correlation_id` nos dois serviços.

### 7. Bônus: tracing com Jaeger (#31)

- **Onde foi usada:** container do Jaeger, OpenTelemetry no gateway e nos serviços, propagação em HTTP e gRPC e print do trace. Parte desse trabalho foi feita em outra conversa com a mesma ferramenta.
- **O que fiz/validei:** conferi o trace único `middleware` → `scheduling` → `medical-record` no Jaeger.

### 8. Bônus: versionamento de API (#32, `feat/versionamento-api`)

- **Onde foi usada:** rotas `/v1` no `scheduling`, rota `/v2` (campo `inicio` no lugar de `data_hora`), testes, contrato OpenAPI e README.
- **Prompts principais:** enviei a issue, `schemas.py`, testes e `public_routes.py`; enviei falhas de `pytest` e `pip` para diagnóstico.
- **O que fiz/validei:** ajustei os testes de observabilidade para `/v1`, rodei os testes no container (33 passed) e testei v1/v2 pelo gateway com os três papéis.

### 9. Integração ponta a ponta (#24, `docs/roteiro-teste.md`, `scripts/e2e.ps1`)

- **Onde foi usada:** roteiro de teste e script PowerShell que executa o fluxo.
- **O que fiz/validei:** executei o roteiro à mão e depois o script (17 passos OK, `X-Correlation-ID` presente nos 4 containers). O roteiro revelou o `/health` ausente no `notification`.

### 10. Relatório técnico (#21)

- **Onde foi usada:** esqueleto, descrição da arquitetura, seção de segurança, dificuldades e lições, e este registro.

**Como a IA foi usada:** a IA gerou código-base, comandos e textos; eu adaptei à estrutura do projeto, executei, corrigi quando a execução real divergiu do previsto e validei cada comportamento. Consigo explicar cada parte (claims do JWT, `algorithms=[...]` explícito, `hmac.compare_digest`, `401` vs `403`, ordem dos middlewares, anti-spoofing de `X-User-*`, retry/breaker, gRPC, propagação de trace).

## Anna Beatriz (gateway e resiliência)

**Ferramenta/modelo:** Claude

### Gateway do middleware (issues #4 a #8, branches `issue-4-roteamento-gateway` a `issue-8-teste-falha-ao-vivo`)

- **Onde foi usada:** planejamento e implementação do gateway em `middleware/app/gateway/` (`config.py`, `router.py`, `correlation.py`, `circuit_breaker.py`), divisão de cada issue em commits pequenos, fluxo de branch e PR, diagnóstico de erros e o script `scripts/falha_ao_vivo.sh`.
- **Prompts principais:**
  - Enviei as instruções que me foram repassadas sobre meu tópico e pedi para explicar como eu poderia prosseguir.
  - Pedi o passo a passo, um passo de cada vez, de roteamento, correlation ID, timeout com retry e backoff, circuit breaker com fallback e teste de falha.
  - Enviei os logs do Docker, o `diff` do `.env` e prints do VS Code e do GitHub para diagnosticar erros.
  - Enviei a lista de issues para descobrir quais eram minhas e como nomear as branches.
- **O que fiz/validei por conta própria:** criei os arquivos e commits, subi os containers e testei cada etapa com `curl`. Validei o roteamento (`/api/scheduling/health`), a propagação do `X-Correlation-ID`, o timeout e o retry (504 em ~11,6 s com o serviço parado) e o circuit breaker (503 em ~0,02 s com o circuito aberto, recuperação para 200 depois de 10 s). Corrigi erros no meu código e no ambiente: arquivo `router.py`, import faltando, indentação do `breaker` e `.env` desatualizado.
- **Como a IA foi usada:** a IA gerou o código-base e os comandos; eu adaptei à estrutura do projeto, executei, corrigi os erros que apareceram e validei o comportamento nos testes.

## Arthur (infraestrutura, Docker e observabilidade)

**Ferramenta/modelo:** [CONFIRMAR]

- **Onde foi usada:** Prometheus e Grafana. Nas demais entregas (compose, healthchecks, `.env`, README).

## Lucas (mensageria)

**Ferramenta/modelo:** [CONFIRMAR]

- **Onde foi usada:** produtor no `scheduling` (#12), consumidor no `notification` (#13), retry, dead-letter queue e idempotência (#14) e reconexão do RabbitMQ (#27).

## Lorenna (serviços de negócio, contratos e observabilidade dos serviços)

**Ferramenta/modelo:** Claude 

- **Onde foi usada:** API REST do `scheduling` com contrato (#9), API REST do `medical-record` com contrato (#10), logs JSON e métricas nos serviços (#11).