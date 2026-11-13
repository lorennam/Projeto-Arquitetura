# Registro de uso de IA/LLM

Este documento registra onde e como o grupo usou IA/LLM no projeto. A responsabilidade técnica é do grupo: tudo que foi gerado com apoio de IA foi revisado e validado por quem o usou.

### Bento

**Ferramenta/modelo:** 

#### 1. Organização do projeto (`docs/divisao.md`, issues e `criar-issues.sh`)

- **Onde foi usada:** divisão das responsabilidades do grupo, lista de issues iniciais e script `criar-issues.sh` com o GitHub CLI.
- **Prompt principal:** enviei o enunciado do projeto e o README do Docker e pedi ajuda para dividir as tarefas entre 5 integrantes (Python, domínio Saúde), usando issues e uma branch por tarefa.

#### 2. Login e emissão de JWT (issue #15, branch `feat/jwt-auth`)

- **Onde foi usada:** planejamento e implementação do `POST /auth/login` no gateway: decisões de design (claims do token, usuários de teste em memória, variáveis no `.env`), estrutura do pacote `middleware/app/auth/` (`config.py`, `users.py`, `tokens.py`, `router.py`), `.gitignore`, `.env.example`, divisão da issue em 10 commits pequenos, seções do README e descrição do PR.
- **Prompts principais:**
  - Enviei o texto da issue #15 e perguntei por onde começar.
  - Perguntei o que pedir ao Arthur (variáveis no `docker-compose.yml`), o que colocar no `.gitignore` e se deveria usar `.env` ou `.env.local`.
  - Pedi para separar a issue no máximo de commits possíveis e conduzir um commit de cada vez.
  - Enviei a estrutura real do `middleware`, o `Dockerfile` e o `main.py` para o código se encaixar no projeto.
  - Enviei o erro do Docker Desktop e os logs do build para diagnóstico.
- **O que eu fiz/validei por conta própria:** criei os arquivos e commits, subi o container e testei o endpoint (login válido retornando o token, senha errada retornando `401`, conferência do payload do JWT).
- **Como a IA foi usada:** a IA gerou o código-base e a documentação; eu adaptei à estrutura do projeto, executei e validei o comportamento, e consigo explicar cada parte (claims `sub`/`role`/`iat`/`exp`, `algorithms=[...]` explícito no decode, `hmac.compare_digest`, `401` genérico, limitações do SHA-256 sem salt).

### Anna Beatriz

**Ferramenta/modelo:** Claude (Anthropic)

#### 1. Gateway do middleware (issues #4 a #8, branches `issue-4-roteamento-gateway` a `issue-8-teste-falha-ao-vivo`)

- **Onde foi usada:** planejamento e implementação do gateway em `middleware/app/gateway/` (`config.py`, `router.py`, `correlation.py`, `circuit_breaker.py`), divisão de cada issue em commits pequenos, fluxo de branch e PR, diagnóstico de erros e o script `scripts/falha_ao_vivo.sh`.
- **Prompts principais:**
  - Enviei as instruções que me foram repassadas sobre meu topico e pedi para explicar como eu poderia prosseguir.
  - Pedi o passo a passo, um passo de cada vez, de roteamento, correlation ID, timeout com retry e backoff, circuit breaker com fallback e teste de falha.
  - Enviei os logs do Docker, o `diff` do `.env` e prints do VS Code e do GitHub para diagnosticar erros.
  - Enviei a lista de issues para descobrir quais eram minhas e como nomear as branches.
- **O que eu fiz/validei por conta própria:** criei os arquivos e commits, subi os containers e testei cada etapa com `curl`. Validei o roteamento (`/api/scheduling/health`), a propagação do `X-Correlation-ID`, o timeout e o retry (504 em ~11,6s com o serviço parado) e o circuit breaker (503 em ~0,02s com o circuito aberto, recuperação para 200 depois de 10s). Corrigi erros no meu código e no ambiente: arquivo router.py, import faltando, indentação do `breaker` e `.env` desatualizado.
- **Como a IA foi usada:** a IA gerou o código-base e os comandos; eu adaptei à estrutura do projeto, executei, corrigi os erros que apareceram e validei o comportamento nos testes.