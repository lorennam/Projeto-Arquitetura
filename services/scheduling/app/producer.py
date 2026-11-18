import json, os, pika

EXCHANGE_NAME = "health.events"
QUEUE_NAME = "notification.consultas"
ROUTING_KEY = "consulta.agendada"

def publicar_consulta_agendada(consulta, correlation_id: str):
    """
    Publica um evento de consulta agendada no RabbitMQ.
    Recebe a consulta já criada e seu identificador de correlação.
    Estabelece uma conexão com o RabbitMq, declara o exchange e a fila,
    vincula ambos pela routing key e publica os dados da consulta
    em formato JSON.

    Agrs: consulta: Objeto ConsultaResponse com os dados da consulta.
          correlation_id (str): Identificador utilizado para rastrear.
          a requisição entre os serviços.

    O evento publicado possui três campos principais:
        event: Nome do evento.
        correlation_id: Identificador de rastreamento.
        data: Dados da consulta.

    A mensagem é publicada como persistente para que possa sobreviver.
    a reinicialização do RabbitMQ, desde que a fila também seja durável. 
    """


    #Obtém as credenciais de acesso ao RabbitMQ pelas variáveis de ambiente.
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER","health_user"),
        os.getenv("RABBITMQ_PASSWORD","change-me")
    )

    #Define os parâmetros necessários para estabelecer a conexão.
    parameters = pika.ConnectionParameters(
        host = os.getenv("RABBITMQ_HOST","rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT","5672")),
        virtual_host=os.getenv("RABBITMQ_VHOST","health"),
        credentials=credentials
    )

    #Abre uma conexão com o servidor RabbitMQ.
    connection = pika.BlockingConnection(parameters)

    try:
        #Cria um cannal para realizar operações de comunicação.
        channel = connection.channel()


        #Declara um exchange do tipo topic.
        #Ele será encarregado de encaminhar eventos conforme a routing key.
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True
        )

        # Declara uma fila durável que receberá os eventos de consulta.
        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True
        )

        #Vincula a fila ao exchange usando a routing key definida.
        channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_NAME,
            routing_key=ROUTING_KEY
        )

        #Monta o conteúdo do evento que será enviado ao RabbitMQ.
        evento = {
            "event": ROUTING_KEY,
            "correlation_id": correlation_id,
            "data":consulta.model_dump(mode="json")
        }

        #Publica a mensagem no exchange.
        channel.basic_publish (
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY,
            body=json.dumps(evento, ensure_ascii=False),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                correlation_id=correlation_id
            ),
            mandatory=True
        )
    finally:
        #Encerra a conexão para liberar os recursos utilizados.
        if connection.is_open:
            connection.close()
