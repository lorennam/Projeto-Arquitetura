# Projeto-Arquitetura


##  Ports

> por enquanto eu já temos as seguitnes portas para os seguintes serviços/containers

> port 8000 para o middleware          
> port 8001 para o schedlling                         
> port 8002 para medical-record                                     
> port 8003 para notification                 


para o serviço de mensagemria to usando o rabbit
para acessar ele online http://localhost:15672
ele vai ser utilizado para a comunicação entre os serviços

pipeline de como rodar o tem ate o momento

da clone
abre a pasta Projeto_Arquetetura
dentro dela mesmo manda um

```
docker compose up --build -d
```

e basicamente ja vai estar rodando em segundo plano


deve aparecer algo nessa pegada no docker ps -a

```
❯ docker ps -a
CONTAINER ID   IMAGE                   COMMAND                  CREATED          STATUS                   PORTS                                                                                        NAMES
64e7aa55ad34   rabbitmq:3-management   "docker-entrypoint.s…"   21 minutes ago   Up 21 minutes            4369/tcp, 5671-5672/tcp, 15671/tcp, 15691-15692/tcp, 25672/tcp, 127.0.0.1:15672->15672/tcp   projeto-arquitetura-rabbitmq-1
7c3e0738d9e8   health-middleware       "uvicorn main:app --…"   21 minutes ago   Up 21 minutes            0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp                                                  projeto-arquitetura-middleware-1
fff5f4d8642c   health-medical-record   "uvicorn main:app --…"   21 minutes ago   Up 21 minutes            8002/tcp                                                                                     projeto-arquitetura-medical-record-1
db6463db0ce5   health-notification     "uvicorn main:app --…"   21 minutes ago   Up 21 minutes            8003/tcp                                                                                     projeto-arquitetura-notification-1
2a32b708bf19   health-scheduling       "uvicorn main:app --…"   21 minutes ago   Up 21 minutes            8001/tcp                                                                                     projeto-arquitetura-scheduling-1
```
