D# Patient Extra Point

Microsserviço responsável pelo cadastro e gerenciamento de pacientes, disponibilizando uma API REST para consulta e manutenção dos dados cadastrais.

## Funcionalidades

- Cadastrar pacientes.
- Listar pacientes cadastrados.
- Consultar paciente por identificador (UUID).
- Atualizar dados cadastrais.
- Excluir pacientes.
- Validar CPF, nome e unicidade do cadastro.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Verifica a saúde do serviço e a conexão com o banco |
| GET | `/v1/pacientes` | Lista os pacientes |
| GET | `/v1/pacientes/{paciente_id}` | Consulta um paciente |
| POST | `/v1/pacientes` | Cadastra um paciente |
| PUT | `/v1/pacientes/{paciente_id}` | Atualiza um paciente |
| DELETE | `/v1/pacientes/{paciente_id}` | Exclui um paciente |

## Persistência

Utiliza PostgreSQL para armazenar os dados dos pacientes, por meio do SQLAlchemy.

A conexão com o banco é configurada pela variável de ambiente `DATABASE_URL`. No ambiente Docker Compose, o serviço utiliza o container `patient-db`.

## Comunicação com o sistema

O serviço disponibiliza sua API REST na porta interna `8004`, conectado à rede Docker `health-network`.

A arquitetura prevê o acesso aos microsserviços por meio de um middleware/API Gateway, que funciona como ponto de entrada das requisições e encaminha cada solicitação ao serviço responsável.

O `patient-extra-point` disponibiliza os endpoints de pacientes para esse encaminhamento. Não foi identificada, na implementação atual, comunicação HTTP direta com outros microsserviços nem consumo ou publicação de mensagens pelo RabbitMQ.

## Observabilidade

- Métricas HTTP disponibilizadas em `/metrics`, utilizando Prometheus.
- Logs estruturados em JSON.
- Propagação do identificador de correlação `X-Correlation-ID`.
- Endpoint `/health` para verificação da saúde da aplicação e do banco de dados.

## Tecnologias

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker
- Prometheus