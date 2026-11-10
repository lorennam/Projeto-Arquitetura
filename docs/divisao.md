# Divisão do Projeto

Middleware distribuído para o domínio de **Saúde**, em Python, com Docker.

## Arquitetura de base

| Componente | Porta | Papel |
| --- | --- | --- |
| `middleware` | 8000 | Gateway próprio: roteamento, autenticação/autorização, resiliência, correlation ID |
| `scheduling` | 8001 | Serviço de agendamento (stub). Publica eventos de consulta |
| `medical-record` | 8002 | Serviço de prontuário (stub). Protegido por papel |
| `notification` | 8003 | Serviço de notificações (stub). Consome eventos |
| `rabbitmq` | 5672 / 15672 | Broker de mensagens (painel em `http://localhost:15672`) |

Apenas o middleware é exposto ao host. Os demais serviços ficam na rede interna do Docker.

**Fluxo síncrono:** cliente → middleware (valida JWT e papel) → serviço de destino (REST).

**Fluxo assíncrono:** `scheduling` publica `consulta.agendada` → RabbitMQ → `notification` consome e "envia" a confirmação.

## Responsáveis

| Pessoa | Área | Entregas principais |
| --- | --- | --- |
| **Arthur** | Infra/Docker e observabilidade | `docker compose up --build` sem intervenção manual, config externalizada (`.env`), healthchecks, README, Prometheus + Grafana (bônus) |
| **Bento** | Segurança | Login com JWT, validação do token no gateway, autorização por papéis (RBAC), proteção do `medical-record` |
| **Anna** | Gateway e resiliência | Roteamento, correlation ID, timeout, retry com backoff, circuit breaker, fallback, teste ao vivo derrubando container |
| **Lucas** | Mensageria | Produtor, consumidor, ack e retry, idempotência, dead-letter queue |
| **Lorenna** | Serviços de negócio e contratos | Endpoints REST de `scheduling` e `medical-record`, contratos OpenAPI, logs JSON e métricas `/metrics` nos serviços |

## Responsabilidades compartilhadas

- **Relatório técnico (3–6 páginas):** cada pessoa escreve a seção da sua área. Uma pessoa faz a revisão final e junta tudo.
- **Documento de tolerância a falhas e consistência:** dupla gateway/resiliência + mensageria.
- **`docs/uso-ia.md`:** todos registram onde e como usaram IA/LLM, a ferramenta/modelo e os prompts principais. A ausência dessa seção no relatório tem penalidade de -3 pontos.
- **Diagrama de arquitetura:** mantido atualizado por quem mudar a arquitetura.
- **Apresentação e demo:** cada integrante apresenta a própria parte. Todos precisam dominar o conteúdo do projeto.

## Fluxo de trabalho no Git

- `main` protegida: nada de push direto, tudo entra por Pull Request.
- **Uma branch por tarefa**, curta e com nome da área: `feat/jwt-auth`, `feat/circuit-breaker`, `feat/rabbit-consumer`, `docs/relatorio-seguranca`.
- Cada tarefa tem uma **issue**. No PR, escrever `Closes #N` na descrição para fechar a issue automaticamente.
- **Revisão cruzada:** todo PR é revisado por pelo menos uma outra pessoa antes do merge.
- Commits pequenos e frequentes, distribuídos ao longo do projeto (histórico concentrado em 1–2 dias é penalizado).
- Mensagens de commit no formato `tipo: descrição` (ex.: `feat: adiciona retry com backoff no gateway`).

## Definição de pronto

Uma tarefa só é fechada quando:

1. O código roda via `docker compose up --build`, sem passos manuais.
2. O comportamento foi testado (ao menos manualmente, com o passo a passo descrito no PR).
3. O README ou os docs foram atualizados, se necessário.
4. Outra pessoa revisou e aprovou o PR.

## Regras que não podemos quebrar

- **Nada de middleware pronto** (Kong, Istio, etc.) como solução. O gateway é nosso. Bibliotecas auxiliares (FastAPI, httpx, pika/aio-pika, PyJWT) são permitidas.
- **Serviços só se falam pela rede**, nunca por import direto.
- O projeto precisa subir com `docker compose up`.
- Declarar o uso de IA/LLM no relatório.