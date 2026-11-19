# Roteiro de Testes Manuais — Projeto Arquitetura

**Issues #12, #13, #14 e #27**
**Ambiente:** Docker Compose | Git Bash | Windows

## Objetivo

Demonstrar na apresentação o fluxo de publicação, consumo, retry, DLQ, idempotência e reconexão com RabbitMQ.

## Importante

- Execute os blocos na ordem.
- Os comandos abaixo partem da raiz do projeto.
- Não execute os testes de falha/reconexão simultaneamente.
- Para chamadas autenticadas, use um token válido do projeto.
- O teste de criação usa a rota já utilizada no projeto: `POST http://localhost:8000/api/scheduling/consultas`
- Se o token expirar, obtenha outro pelo endpoint de login usado no projeto.
- O teste de retry usa uma mensagem propositalmente inválida.
- O teste de idempotência usa IDs de mensagem exclusivos.

---

## 0. Preparar e subir o ambiente

```bash
docker compose up -d --build

docker compose ps
```

**Resultado esperado:**

- middleware: Up (healthy)
- scheduling: Up (healthy)
- rabbitmq: Up (healthy)
- notification-consumer: Up

Ver logs dos serviços:

```bash
docker compose logs --tail=30 middleware scheduling notification-consumer rabbitmq
```

---

## 1. Issue #12 — Publicação de eventos pelo produtor

Defina um token válido obtido pelo mecanismo de autenticação do projeto:

```bash
export TOKEN="COLE_SEU_TOKEN_AQUI"
```

Crie uma consulta para disparar o evento `consulta.agendada`:

```bash
curl -i -X POST "http://localhost:8000/api/scheduling/consultas" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Correlation-ID: apresentacao-issue-12" \
  -d '{
    "paciente_id": "paciente-001",
    "profissional_id": "medico-001",
    "data_hora": "2030-05-20T14:30:00Z",
    "motivo": "Teste de publicacao do produtor"
  }'
```

**Resultado esperado:**

- A API aceita a criação da consulta.
- O produtor publica o evento `consulta.agendada` no exchange `health.events`.
- O evento carrega `correlation_id`.
- O `message_id` é preenchido com o ID da consulta.

Confira os logs:

```bash
docker compose logs --tail=50 scheduling
```

---

## 2. Issue #13 — Consumo da mensagem

Confira os logs do consumidor:

```bash
docker compose logs --tail=80 notification-consumer
```

**Resultado esperado:**

- Consumidor conectado ao RabbitMQ.
- Consumidor aguardando mensagens.
- Notificação de consulta agendada exibida nos logs.
- Mensagem confirmada com ACK após processamento.

Confira filas, consumidores e mensagens:

```bash
docker compose exec rabbitmq rabbitmqctl list_queues -p health name messages_ready messages_unacknowledged consumers
```

**Resultado esperado:**

- `notification.consultas` com consumidor conectado.
- Mensagens processadas não permanecem acumuladas na fila.
- `messages_unacknowledged` deve voltar a zero após o processamento.

---

## 3. Issue #14 — Retry e Dead Letter Queue (DLQ)

Este teste publica uma mensagem inválida de propósito. Ela deve falhar na validação, passar pelo retry e terminar na DLQ após o limite configurado.

Execute:

```bash
docker compose exec -T notification-consumer python -c "import os,json,pika; p=pika.ConnectionParameters(host=os.getenv('RABBITMQ_HOST','rabbitmq'),port=int(os.getenv('RABBITMQ_PORT','5672')),virtual_host=os.getenv('RABBITMQ_VHOST','health'),credentials=pika.PlainCredentials(os.getenv('RABBITMQ_USER','health_user'),os.getenv('RABBITMQ_PASSWORD','change-me'))); c=pika.BlockingConnection(p); ch=c.channel(); ch.basic_publish(exchange='health.events',routing_key='consulta.agendada',body=json.dumps({'event':'consulta.agendada','data':{}}),properties=pika.BasicProperties(message_id='apresentacao-retry-001',correlation_id='apresentacao-retry-001',delivery_mode=2)); print('Mensagem inválida publicada'); c.close()"
```

Aguarde aproximadamente 20 segundos (o retry padrão é de 5 segundos).

Confira os logs:

```bash
docker compose logs --since=2m notification-consumer
```

Confira as filas:

```bash
docker compose exec rabbitmq rabbitmqctl list_queues -p health name messages_ready messages_unacknowledged consumers
```

**Resultado esperado:**

- A mensagem falha na validação.
- O contador de tentativas aumenta.
- A mensagem é reenviada para retry.
- Após o limite de 3 tentativas, vai para `notification.consultas.dlq`.
- A mensagem não fica presa indefinidamente na fila principal.

> **Observação:** Se a DLQ já contiver mensagens de testes anteriores, compare a quantidade antes e depois do teste.

---

## 4. Issue #14 — Idempotência (mensagem duplicada)

Este teste publica duas vezes o mesmo `message_id`. O consumidor deve processar a primeira mensagem e ignorar a segunda.

Execute:

```bash
docker compose exec -T notification-consumer python -c "import os,json,pika; p=pika.ConnectionParameters(host=os.getenv('RABBITMQ_HOST','rabbitmq'),port=int(os.getenv('RABBITMQ_PORT','5672')),virtual_host=os.getenv('RABBITMQ_VHOST','health'),credentials=pika.PlainCredentials(os.getenv('RABBITMQ_USER','health_user'),os.getenv('RABBITMQ_PASSWORD','change-me'))); c=pika.BlockingConnection(p); ch=c.channel(); body=json.dumps({'event':'consulta.agendada','correlation_id':'apresentacao-idempotencia-001','data':{'id':9001,'paciente_id':'paciente-001','data_hora':'2030-05-21T14:00:00Z'}}); props=pika.BasicProperties(message_id='apresentacao-idempotencia-001',correlation_id='apresentacao-idempotencia-001',delivery_mode=2); ch.basic_publish(exchange='health.events',routing_key='consulta.agendada',body=body,properties=props); ch.basic_publish(exchange='health.events',routing_key='consulta.agendada',body=body,properties=props); print('Duas mensagens com o mesmo message_id foram publicadas'); c.close()"
```

Confira os logs:

```bash
docker compose logs --since=1m notification-consumer
```

**Resultado esperado:**

- Uma notificação processada com sucesso.
- Uma ocorrência de "Mensagem duplicata ignorada".
- Não deve haver uma segunda notificação processada para o mesmo ID.

Confira os registros persistidos no SQLite:

```bash
docker compose exec notification-consumer python -c "import os,sqlite3; c=sqlite3.connect(os.getenv('IDEMPOTENCY_DB_PATH','/data/processed_messages.db')); print(*c.execute(\"SELECT message_id, processed_at FROM processed_messages WHERE message_id='apresentacao-idempotencia-001'\").fetchall(),sep='\\n'); c.close()"
```

**Resultado esperado:**

- Apenas um registro para `apresentacao-idempotencia-001`.

---

## 5. Issue #27 — Reconexão do consumidor com RabbitMQ

Primeiro, acompanhe os logs do consumidor em um terminal:

```bash
docker compose logs -f notification-consumer
```

Em outro terminal, pare o RabbitMQ:

```bash
docker compose stop rabbitmq
```

**Resultado esperado:**

- O consumidor detecta a perda de conexão.
- Os logs mostram a falha e as tentativas de reconexão.

Inicie o RabbitMQ novamente:

```bash
docker compose start rabbitmq
```

Aguarde o RabbitMQ ficar saudável:

```bash
docker compose ps
```

**Resultado esperado:**

- RabbitMQ volta para Up (healthy).
- O consumidor restabelece a conexão.
- O consumidor volta a aguardar mensagens sem precisar recriar o container.

Para encerrar o acompanhamento de logs, pressione `Ctrl+C`. Isso encerra apenas o comando de logs, não os containers.

Confira novamente:

```bash
docker compose logs --since=3m notification-consumer
```

---

## 6. Verificação final

```bash
docker compose ps

docker compose exec rabbitmq rabbitmqctl list_queues -p health name messages_ready messages_unacknowledged consumers

docker compose logs --tail=50 scheduling notification-consumer
```

**Resultado esperado:**

- Serviços ativos.
- Consumidor conectado.
- Nenhuma mensagem não confirmada presa (`messages_unacknowledged = 0`).
- Filas de retry e principal sem mensagens pendentes, salvo mensagens de testes anteriores.
- A DLQ pode conter a mensagem inválida do teste de retry.

---

## Resumo para apresentação

| Issue | Tema | O que demonstrar |
|-------|------|------------------|
| #12 | Produtor | Cria uma consulta pela API e demonstra a publicação do evento no RabbitMQ. |
| #13 | Consumidor | Demonstra o recebimento, processamento e ACK manual da mensagem. |
| #14 | Retry e DLQ | Publica uma mensagem inválida, demonstra as tentativas e o encaminhamento para a Dead Letter Queue. |
| #14 | Idempotência | Publica duas mensagens com o mesmo `message_id` e demonstra que somente uma é processada. |
| #27 | Reconexão | Interrompe o RabbitMQ, demonstra as tentativas de reconexão e restaura o broker para comprovar a retomada do consumidor. |