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

```powershell
docker compose up --build -d
docker compose ps
```

Todos os serviços devem estar `healthy` (o `notification-consumer` não tem healthcheck e só precisa estar `Up`).

Limpe a fila de falhas (DLQ) para o resultado ficar limpo:

```powershell
docker compose exec rabbitmq rabbitmqctl purge_queue -p health notification.consultas.dlq
```

Senhas de teste: `paciente123`, `medico123` e `admin123` (ou as do `.env`).

## 1. Login

```powershell
function Get-Token($u, $p, $cid) {
  (Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login `
    -Headers @{ "X-Correlation-ID" = $cid } `
    -ContentType "application/json" `
    -Body "{`"username`":`"$u`",`"password`":`"$p`"}").access_token
}

$medico   = Get-Token "medico"   "medico123"   "demo-e2e-login"
$paciente = Get-Token "paciente" "paciente123" "demo-e2e-login"
$admin    = Get-Token "admin"    "admin123"    "demo-e2e-login"
```

**Esperado:** três tokens JWT, sem erro. Cole um token em jwt.io e confira `sub`, `role` e `exp` (30 min).

## 2. Fluxo completo

O ID `demo-e2e-001` será usado em toda a cadeia para o rastreio da seção 4.

### 2.1 Parar o consumidor para ver a mensagem na fila

```powershell
docker compose stop notification-consumer
```

### 2.2 Criar prontuário e agendar consulta (médico)

```powershell
$h = @{ Authorization = "Bearer $medico"; "X-Correlation-ID" = "demo-e2e-001" }

# prontuário do paciente (para o gRPC responder existe=true)
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/medical-record/v1/pacientes/demo-paciente/registros `
  -Headers $h -ContentType "application/json" `
  -Body '{"profissional_id":"medico-001","tipo":"anotacao","descricao":"registro do roteiro"}'

# agendamento
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/scheduling/v1/consultas `
  -Headers $h -ContentType "application/json" `
  -Body '{"paciente_id":"demo-paciente","profissional_id":"demo-medico","data_hora":"2032-01-10T10:00:00Z"}'
```

**Esperado:** `201` nas duas chamadas.

### 2.3 Evento na fila

```powershell
docker compose exec rabbitmq rabbitmqctl list_queues -p health name messages
```

**Esperado:** `notification.consultas` com **1** mensagem (parada, pois o consumidor está desligado).

### 2.4 Consumir a notificação

```powershell
docker compose start notification-consumer
Start-Sleep -Seconds 8
docker compose logs notification-consumer --tail 10
docker compose exec rabbitmq rabbitmqctl list_queues -p health name messages
```

**Esperado:** log `Notificação de consulta agendada: ... Paciente=demo-paciente ... correlation_id=demo-e2e-001` e `Notificação processada com sucesso!`. Fila `notification.consultas` volta a **0** e a DLQ continua em **0**.

### 2.5 Consulta ao prontuário com o papel correto

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/medical-record/v1/pacientes/demo-paciente/registros `
  -Headers @{ Authorization = "Bearer $medico" }
```

**Esperado:** `200` com o registro criado (somente o papel `doctor` acessa).

## 3. Acessos negados

_(a completar)_

## 4. Rastreio do Correlation ID

_(a completar)_

## 5. Resultados esperados

_(a completar)_