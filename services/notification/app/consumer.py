
import json
import os
import time
import pika

# Configurações da comunicação com o RabbitMQ.
EXCHANGE_NAME = "health.events"
QUEUE_NAME = "notification.consultas"
ROUTING_KEY = "consulta.agendada"


# Cria uma conexão com o servidor RabbitMQ.
def conectar_rabbitmq():

    # Cria as credenciais de autenticação usando variáveis de ambiente.
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER", "health_user"),
        os.getenv("RABBITMQ_PASSWORD", "change-me")
    )

    # Define os parâmetros necessários para estabelecer a conexão.
    parameters = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        virtual_host=os.getenv("RABBITMQ_VHOST", "health"),
        credentials=credentials
    )

    # Tenta estabelecer a conexão até o RabbitMQ estar disponível.
    while True:
        try:
            print("Tentando conectar ao RabbitMQ...", flush=True)
            connection = pika.BlockingConnection(parameters)
            print("Conexão com RabbitMQ estabelecida!", flush=True)
            return connection

        except pika.exceptions.AMQPConnectionError as erro:
            print(f"Falha na conexão com RabbitMQ: {erro}", flush=True)
            print("Nova tentativa em 5 segundos...", flush=True)
            time.sleep(5)


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

    # Estabelece a conexão com o RabbitMQ.
    connection = conectar_rabbitmq()

    try:
        # Cria um canal de comunicação dentro da conexão.
        channel = connection.channel()

        # Configura a exchange, a fila e o vínculo entre elas.
        configurar_fila(channel)

        # Registra o callback que será executado ao receber uma mensagem.
        channel.basic_consume(
            queue=QUEUE_NAME,
            on_message_callback=callback_notificacao,
            auto_ack=False
        )

        # Inicia o consumo e mantém o serviço aguardando mensagens.
        print("Consumidor aguardando mensagens...", flush=True)
        channel.start_consuming()

    finally:
        # Fecha a conexão quando o consumo for encerrado.
        if connection.is_open:
            connection.close()


# Executa o consumidor quando o arquivo é iniciado diretamente.
if __name__ == "__main__":
    iniciar_consumidor()
