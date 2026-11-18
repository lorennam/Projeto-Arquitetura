
import json
import os
import time
import pika
import sqlite3

RETRY_QUEUE = "notification.consultas.retry"
DLQ_QUEUE = "notification.consultas.dlq"

DLQ_EXCHANGE = "health.dlx"
MAX_RETRIES = int(os.getenv("RABBITMQ_MAX_RETRIES","3"))
MESSAGE_RETRY_DELAY = int(os.getenv("RABBITMQ_MESSAGE_RETRY_DELAY","5000"))

# Configurações da comunicação com o RabbitMQ.
EXCHANGE_NAME = "health.events"
QUEUE_NAME = "notification.consultas"
ROUTING_KEY = "consulta.agendada"
RETRY_DELAY = int(os.getenv("RABBITMQ_RETRY_DELAY", "5"))

def inicializar_banco():
    caminho = os.getenv("IDEMPOTENCY_DB_PATH", "/data/processed_messages.db")

    diretorio = os.path.dirname(caminho)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)

    with sqlite3.connect(caminho) as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
            message_id TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def registrar_mensagem(message_id):
    caminho = os.getenv("IDEMPOTENCY_DB_PATH", "/data/processed_messages.db")

    with sqlite3.connect(caminho) as conexao:
        cursor = conexao.execute(
            "INSERT OR IGNORE INTO processed_messages (message_id) VALUES (?)",
            (message_id,)
            )
        return cursor.rowcount > 0





def conectar_rabbitmq():
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER", "health_user"),
        os.getenv("RABBITMQ_PASSWORD", "change-me")
    )

    parameters = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        virtual_host=os.getenv("RABBITMQ_VHOST", "health"),
        credentials=credentials
    )

    while True:
        try:
            print("Consumidor: tentando conectar ao RabbitMQ...", flush=True)

            connection = pika.BlockingConnection(parameters)

            print("Consumidor: conexão estabelecida!", flush=True)

            return connection

        except (pika.exceptions.AMQPConnectionError, OSError) as erro:
            print(f"Consumidor: falha na conexão: {erro}", flush=True)
            print(f"Consumidor: nova tentativa em {RETRY_DELAY} segundos...", flush=True)
            time.sleep(RETRY_DELAY)


def configurar_fila(channel):

    # Declara a exchange de eventos.
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True
    )

    channel.exchange_declare(
        exchange=DLQ_EXCHANGE,
        exchange_type="direct",
        durable=True
    )

    channel.exchange_declare(
        exchange="notification.retry",
        exchange_type="direct",
        durable=True
    )

    # Declara a fila que receberá as notificações.
    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True
    )

    # Vincula a fila à exchange usando a routing key do evento.
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=QUEUE_NAME,
        routing_key=ROUTING_KEY
    )

    channel.queue_declare(
        queue=RETRY_QUEUE,
        durable=True,
        arguments= {
            "x-message-ttl": MESSAGE_RETRY_DELAY,
            "x-dead-letter-exchange": EXCHANGE_NAME,
            "x-dead-letter-routing-key": ROUTING_KEY
        }
    )

    channel.queue_bind(
        exchange="notification.retry",
        queue=RETRY_QUEUE,
        routing_key="consulta.retry"
    )

    channel.queue_declare(
        queue=DLQ_QUEUE,
        durable=True
    )

    channel.queue_bind(
        exchange=DLQ_EXCHANGE,
        queue=DLQ_QUEUE,
        routing_key="consulta.failed"
    )

    # Limita a entrega a uma mensagem por vez enquanto a anterior não for confirmada.
    channel.confirm_delivery()
    channel.basic_qos(prefetch_count=1)


def encaminhar_mensagem(channel, exchange, routing_key, body, properties, headers=None):

    novas_properties = pika.BasicProperties (
        content_type=properties.content_type,
        delivery_mode=2,
        correlation_id=properties.correlation_id,
        message_id=properties.message_id,
        headers=headers if headers is not None else properties.headers
    )

    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=body,
        properties=novas_properties,
        mandatory=True
    )



def processar_notificacao(body, message_id):

    # Converte os bytes recebidos do RabbitMQ para um objeto Python.
    mensagem = json.loads(body)

    # Verifica se o evento recebido é o esperado.
    if mensagem.get("event") != ROUTING_KEY:
        raise ValueError("Tipo de evento desconhecido.")

    # Extrai os dados da consulta.
    consulta = mensagem["data"]

    if not all(campo in consulta for campo in ("id","paciente_id","data_hora")):
        raise ValueError("Dados da consulta incompletos.")

    if not message_id:
        raise ValueError("Mensagem recebida sem message_id.")

    if not registrar_mensagem(message_id):
        print(f"Mensagem duplicata ignorada: {message_id}", flush=True)
        return False

    # Extrai o identificador de correlação para rastrear a operação.
    correlation_id = mensagem.get("correlation_id")

    # Simula o envio de uma notificação ao paciente.
    print(
        f"Notificação de consulta agendada: "
        f"Consulta={consulta['id']}, "
        f"Paciente={consulta['paciente_id']}, "
        f"Data={consulta['data_hora']}, "
        f"correlation_id={correlation_id}",
        flush=True
    )

    return True



def callback_notificacao(channel, method, properties, body):

    headers = properties.headers or {}

    try:
        tentativas = int(headers.get("x-retry-count", 0))
    except (TypeError, ValueError):
        tentativas = 0

    try:
        processada = processar_notificacao(body, properties.message_id)

    except Exception as erro:

        print(f"Erro ao processar notificação: {erro}", flush=True)

        try:
            if tentativas < MAX_RETRIES:

                novas_tentativas = tentativas + 1

                novos_headers = {
                    **headers,
                    "x-retry-count": novas_tentativas
                }

                encaminhar_mensagem(
                    channel,
                    "notification.retry",
                    "consulta.retry",
                    body,
                    properties,
                    novos_headers
                )

                print(
                    f"Mensagem encaminhada para retry. Tentativa: {novas_tentativas}/{MAX_RETRIES}",
                    flush=True
                )

            else:

                encaminhar_mensagem(
                    channel,
                    DLQ_EXCHANGE,
                    "consulta.failed",
                    body,
                    properties,
                    headers
                )

                print(
                    "Limite de tentativas atingido. Mensagem enviada para DLQ.",
                    flush=True
                )

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as erro_encaminhamento:

            print(
                f"Erro ao encaminhar mensagem: {erro_encaminhamento}",
                flush=True
            )

            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=True
            )

    else:
        if processada:
            print("Notificação processada com sucesso!",flush=True)

        channel.basic_ack(delivery_tag=method.delivery_tag)


def iniciar_consumidor():
    inicializar_banco()
    while True:
        connection = None

        try:
            # Estabelece a conexão com o RabbitMQ.
            connection = conectar_rabbitmq()

            # Cria um canal de comunicação.
            channel = connection.channel()

            # Configura a exchange, a fila e o vínculo.
            configurar_fila(channel)

            # Registra o callback para processar as mensagens.
            channel.basic_consume(
                queue=QUEUE_NAME,
                on_message_callback=callback_notificacao,
                auto_ack=False
            )

            # Inicia o consumo das mensagens.
            print("Consumidor aguardando mensagens...", flush=True)
            channel.start_consuming()

        except (
            pika.exceptions.AMQPConnectionError,
            pika.exceptions.ConnectionWrongStateError,
            pika.exceptions.ChannelWrongStateError,
            OSError
        ) as erro:

            print(f"Consumidor: conexão perdida: {erro}", flush=True)
            print(f"Consumidor: tentando reconectar em {RETRY_DELAY} segundos...", flush=True)

            time.sleep(RETRY_DELAY)

        finally:
            if connection is not None and connection.is_open:
                try:
                    connection.close()
                except (pika.exceptions.AMQPError, OSError) as erro:
                    print(f"Consumidor: erro ao fechar conexão: {erro}",flush=True)



# Executa o consumidor quando o arquivo é iniciado diretamente.
if __name__ == "__main__":
    iniciar_consumidor()
