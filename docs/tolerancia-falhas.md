# Estratégia de Tolerância a Falhas e Consistência

Este documento descreve como o middleware de saúde se comporta diante de falhas
e qual modelo de consistência foi adotado entre os serviços.

## 1. Objetivo e escopo

Definir, para cada componente do sistema (`middleware`, `scheduling`,
`medical-record`, `notification` e `rabbitmq`), o que acontece quando ele
fica indisponível, e justificar o modelo de consistência escolhido.

| Componente | Papel | Comunicação |
| --- | --- | --- |
| `middleware` | Gateway: roteamento, JWT, RBAC, resiliência | HTTP (síncrona) |
| `scheduling` | Agendamento de consultas | HTTP, RabbitMQ (produtor), gRPC (cliente) |
| `medical-record` | Prontuário | HTTP, gRPC (servidor) |
| `notification` | Confirmação de consultas | HTTP, RabbitMQ (consumidor) |
| `rabbitmq` | Broker de mensagens | AMQP |

## 2. Mecanismos de resiliência do gateway

As chamadas do gateway aos serviços (`/api/<serviço>/...`) passam por timeout,
retry com backoff exponencial e circuit breaker, implementados em
`middleware/app/gateway/`.

| Mecanismo | Valor padrão | Variável de ambiente |
| --- | --- | --- |
| Timeout por tentativa | 5 s | `GATEWAY_TIMEOUT_SECONDS` |
| Timeout de conexão (por tentativa) | 2 s | `GATEWAY_CONNECT_TIMEOUT_SECONDS` |
| Retries | 3 (4 tentativas no total) | `GATEWAY_MAX_RETRIES` |
| Base do backoff | 0,5 s (0,5 s, 1 s, 2 s) | `GATEWAY_BACKOFF_BASE_SECONDS` |
| Falhas para abrir o breaker | 3 | `GATEWAY_CB_FAILURE_THRESHOLD` |
| Tempo até tentar recuperar | 10 s | `GATEWAY_CB_RECOVERY_SECONDS` |

### Retry com backoff

Falhas de rede (`httpx.RequestError`: conexão recusada, timeout) são repetidas
até 3 vezes, esperando `0,5 × 2^n` segundos entre as tentativas. Respostas HTTP
do serviço (inclusive 4xx e 5xx) **não** são repetidas: são repassadas ao cliente.

### Circuit breaker

Há um breaker **por serviço**, então a queda de um serviço não bloqueia os outros.

| Estado | Comportamento |
| --- | --- |
| `closed` | Requisições passam normalmente. |
| `open` | Após 3 requisições que esgotaram os retries. O gateway responde `503` com `Retry-After: 10` **sem chamar o serviço**. |
| `half-open` | Passados 10 s, as requisições voltam a passar. Um sucesso fecha o breaker; uma falha o reabre. |

Cada requisição que esgota os retries conta como **uma** falha para o breaker.

### Respostas de erro

| Situação | Resposta |
| --- | --- |
| Serviço inexistente | `404` |
| Serviço sem resposta (container parado): timeouts em todas as tentativas | `504`, após ~11,6 s (4 × 2 s de conexão + 3,5 s de backoff) |
| Serviço recusando conexão ou DNS falhando, após retries | `503` |
| Breaker aberto | `503` imediato, com `Retry-After: 10` |

## 3. Consistência escolhida e justificativa

**Modelo: consistência eventual entre serviços, forte dentro de cada serviço.**

| Escopo | Modelo | Motivo |
| --- | --- | --- |
| Dentro de um serviço (ex.: conflito de horário no `scheduling`) | Forte | Cada serviço tem uma única instância e seu próprio repositório; a checagem e a gravação acontecem na mesma requisição. |
| `scheduling` → `notification` (evento `consulta.agendada`) | Eventual | A notificação é publicada via RabbitMQ e processada depois; entre a gravação da consulta e a notificação há um intervalo em que os estados diferem. |
| `scheduling` → `medical-record` (gRPC) | Consulta síncrona, informativa | Lê o estado atual do prontuário; não altera dados nem bloqueia o agendamento. |

### Justificativa

- **A notificação não precisa ser imediata.** Atrasar o aviso ao paciente em segundos
  é aceitável; travar o agendamento por causa dele não é.
- **Desacoplamento:** o `scheduling` não depende do `notification` estar no ar.
- **Disponibilidade acima de consistência imediata** (teorema CAP): preferimos aceitar
  respostas ligeiramente defasadas a recusar agendamentos.

### Como a eventual consistência é mantida

- **Entrega at-least-once:** mensagens persistentes (`delivery_mode=2`), filas duráveis,
  `ack` manual no consumidor e confirmação de publicação (`confirm_delivery`).
- **Idempotência:** o consumidor registra o `message_id` em SQLite e ignora duplicatas.
- **Retry e DLQ:** falhas de processamento voltam por uma fila de retry (TTL de 5 s)
  até 3 vezes e então seguem para a DLQ `notification.consultas.dlq`, sem perda.

## 4. Comportamento na queda de cada componente

Nenhum serviço tem política de `restart` no `docker-compose.yml`: um container
que cai **permanece parado** até alguém subi-lo de novo. Os repositórios são em
memória, então os dados de `scheduling` e `medical-record` se perdem na queda.

### 4.1 scheduling

| Aspecto | Comportamento |
| --- | --- |
| Chamadas pelo gateway | `504` após ~11,6 s nas 3 primeiras (timeouts + retries); depois o breaker abre e o gateway responde `503` imediato com `Retry-After: 10` |
| Recuperação | Passados 10 s o breaker entra em `half-open`; a primeira chamada bem-sucedida o fecha |
| Outros serviços | Não são afetados (breaker por serviço) |
| Eventos | Nenhum novo evento `consulta.agendada` é publicado; os já enfileirados continuam sendo processados |

### 4.2 medical-record

| Aspecto | Comportamento |
| --- | --- |
| Chamadas pelo gateway | Mesmo comportamento do `scheduling` (504, depois 503 com breaker aberto) |
| Chamada gRPC do `scheduling` | Timeout de 2 s; o erro é registrado em log e o agendamento **continua** (a consulta ao prontuário é informativa) |

### 4.3 notification

| Componente | Comportamento |
| --- | --- |
| API HTTP | Mesmo comportamento dos demais (504, depois 503) |
| Consumidor | Com o consumidor parado, as mensagens se acumulam na fila durável `notification.consultas` e são processadas quando ele volta. O registro de idempotência fica em volume (`notification_data`) e sobrevive à queda |

A API e o consumidor são containers separados: a queda de um não afeta o outro.

### 4.4 middleware (gateway)

É o único ponto de entrada e **não é replicado**: se cair, os clientes externos
perdem o acesso a todos os serviços. Internamente, os serviços e o fluxo
assíncrono (RabbitMQ) continuam funcionando, pois não dependem do gateway.
Mitigação futura: múltiplas réplicas atrás de um balanceador.

_(a completar)_

## 5. Como foi testado

_(a completar)_

## 6. Limitações conhecidas

_(a completar)_