# Roteiro de teste ponta a ponta

Roteiro para validar o fluxo completo do middleware e servir de base para a demo.
Os comandos são para PowerShell, na raiz do repositório.

## Cenários cobertos

| # | Cenário | Resultado esperado |
| --- | --- | --- |
| 1 | Login com cada papel | `200` com JWT |
| 2 | Agendar consulta (médico) | `201`, evento publicado na fila |
| 3 | Evento na fila e consumo | Mensagem enfileirada e depois consumida pelo `notification` |
| 4 | Consulta ao prontuário (médico) | `200` |
| 5 | Sem token | `401` |
| 6 | Papel sem permissão | `403` |
| 7 | Correlation ID | Mesmo ID nos logs do gateway, do serviço e do consumidor |

## 0. Pré-requisitos

_(a completar)_

## 1. Login

_(a completar)_

## 2. Fluxo completo

_(a completar)_

## 3. Acessos negados

_(a completar)_

## 4. Rastreio do Correlation ID

_(a completar)_

## 5. Resultados esperados

_(a completar)_