# Relatório Técnico: Middleware Distribuído para o Domínio de Saúde

Equipe: Arthur, Bento, Anna, Lucas e Lorenna.

## 1. Descrição da arquitetura

O sistema é um middleware distribuído para o domínio de saúde, em Python, executado com `docker compose`. O **gateway** (`middleware`) é implementado por nós, sem middleware pronto, e é o único componente exposto ao host.

![Diagrama de arquitetura](img/arquitetura.png)

| Componente | Papel |
| --- | --- |
| `middleware` (8000) | Gateway: roteamento, JWT, RBAC, correlation ID, timeout, retry, circuit breaker |
| `scheduling` (8001) | Agendamento de consultas; produtor de eventos; cliente gRPC |
| `medical-record` (8002) | Prontuário; servidor gRPC |
| `notification` (8003) | API de notificações e consumidor de eventos |
| `rabbitmq` | Broker de mensagens |
| `jaeger`, `prometheus`, `grafana` | Tracing, métricas e painéis |

**Fluxo síncrono:** cliente → gateway (valida JWT e papel) → serviço (REST).
**Fluxo assíncrono:** `scheduling` publica `consulta.agendada` → RabbitMQ → `notification` consome.
**Chamada interna:** `scheduling` → `medical-record` por gRPC, para consultar se o paciente tem prontuário.

Os serviços só se comunicam pela rede, nunca por import direto. Cada serviço tem seu próprio repositório de dados em memória.

## 2. Decisões técnicas e justificativas

### 2.1 Segurança (JWT e RBAC)
### 2.2 Gateway e resiliência
### 2.3 Mensageria e consistência
### 2.4 Serviços de negócio e contratos
### 2.5 Observabilidade e tracing
### 2.6 Comunicação interna via gRPC
### 2.7 Versionamento de API
### 2.8 Infraestrutura

## 3. Dificuldades e lições aprendidas

_(a completar)_

## 4. Uso de IA/LLM

_(a completar)_