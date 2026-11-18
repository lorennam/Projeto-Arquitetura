
import json
import os
import time
import pika

# Configurações da comunicação com o RabbitMQ.
EXCHANGE_NAME = "health.events"
QUEUE_NAME = "notification.consultas"
ROUTING_KEY = "consulta.agendada"
RETRY_DELAY = int(os.getenv("RABBITMQ_RETRY_DELAY", "5"))


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

    # Limita a entrega a uma mensagem por vez enquanto a anterior não for confirmada.
    channel.basic_qos(prefetch_count=1)


def processar_notificacao(body):

    # Converte os bytes recebidos do RabbitMQ para um objeto Python.
    mensagem = json.loads(body)

    # Verifica se o evento recebido é o esperado.
    if mensagem.get("event") != ROUTING_KEY:
        raise ValueError("Tipo de evento desconhecido.")

    # Extrai os dados da consulta.
    consulta = mensagem["data"]

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


def callback_notificacao(channel, method, properties, body):

    try:
        # Processa a notificação.
        processar_notificacao(body)

        # Confirma ao RabbitMQ que a mensagem foi processada com sucesso.
        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as erro:

        # Registra o erro ocorrido durante o processamento.
        print(f"Erro ao processar notificação: {erro}", flush=True)

        # Devolve a mensagem para a fila, permitindo uma nova tentativa.
        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True
        )



def iniciar_consumidor():

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
