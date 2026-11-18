
import json
import os
import time
import pika

EXCHANGE_NAME = "health.events"
QUEUE_NAME = "notification.consultas"
ROUTING_KEY = "consulta.agendada"
RETRY_DELAY = int(os.getenv("RABBITMQ_RETRY_DELAY", "5"))


def publicar_consulta_agendada(consulta, correlation_id: str):
    """
    Publica um evento de consulta agendada no RabbitMQ.
    Tenta novamente caso o broker esteja indisponível ou a conexão caia.
    """

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

    evento = {
        "event": ROUTING_KEY,
        "correlation_id": correlation_id,
        "data": consulta.model_dump(mode="json")
    }

    mensagem = json.dumps(evento, ensure_ascii=False)

    while True:
        connection = None

        try:
            # Tenta estabelecer uma conexão com o RabbitMQ.
            print("Produtor: tentando conectar ao RabbitMQ...", flush=True)

            connection = pika.BlockingConnection(parameters)

            print("Produtor: conexão estabelecida!", flush=True)

            # Cria o canal de comunicação.
            channel = connection.channel()

            # Ativa as confirmações de publicação.
            channel.confirm_delivery()

            # Declara o exchange de eventos.
            channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type="topic",
                durable=True
            )

            # Declara a fila que receberá os eventos.
            channel.queue_declare(
                queue=QUEUE_NAME,
                durable=True
            )

            # Vincula a fila ao exchange.
            channel.queue_bind(
                exchange=EXCHANGE_NAME,
                queue=QUEUE_NAME,
                routing_key=ROUTING_KEY
            )

            # Publica o evento no RabbitMQ.
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=ROUTING_KEY,
                body=mensagem,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                    correlation_id=correlation_id
                ),
                mandatory=True
            )

            print(
                f"Produtor: evento {ROUTING_KEY} publicado com sucesso!",
                flush=True
            )

            return

        except (
            pika.exceptions.AMQPConnectionError,
            pika.exceptions.ConnectionWrongStateError,
            pika.exceptions.ChannelWrongStateError,
            OSError
        ) as erro:

            # Registra a falha e prepara uma nova tentativa.
            print(f"Produtor: falha na comunicação: {erro}", flush=True)
            print(
                f"Produtor: nova tentativa em {RETRY_DELAY} segundos...",
                flush=True
            )

        finally:
            # Fecha a conexão antes de iniciar uma nova tentativa.
            if connection is not None and connection.is_open:
                try:
                    connection.close()
                except (pika.exceptions.AMQPError, OSError) as erro:
                    print(f"Produtor: erro ao fechar conexão: {erro}",flush=True)

        time.sleep(RETRY_DELAY)
