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

_(a completar: timeout, retry com backoff, circuit breaker, fallback)_

## 3. Consistência escolhida e justificativa

_(a completar)_

## 4. Comportamento na queda de cada componente

_(a completar)_

## 5. Como foi testado

_(a completar)_

## 6. Limitações conhecidas

_(a completar)_