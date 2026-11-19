# Teste ponta a ponta: login -> agendar -> fila -> notificacao -> prontuario -> 401/403 -> correlation id
$ErrorActionPreference = "Stop"
$base = "http://localhost:8000"
$cid  = "e2e-" + (Get-Date -Format "HHmmss")
$falhas = 0

function Check($nome, $ok) {
  if ($ok) { Write-Host "[OK]     $nome" -ForegroundColor Green }
  else { Write-Host "[FALHOU] $nome" -ForegroundColor Red; $script:falhas++ }
}

function Get-Status($url, $token, $metodo = "GET") {
  $headers = @{}
  if ($token) { $headers["Authorization"] = "Bearer $token" }
  try {
    $r = Invoke-WebRequest -Method $metodo -Uri $url -Headers $headers -UseBasicParsing
    return [int]$r.StatusCode
  } catch {
    return [int]$_.Exception.Response.StatusCode
  }
}

function Get-Token($u, $p) {
  (Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType "application/json" `
    -Body "{`"username`":`"$u`",`"password`":`"$p`"}").access_token
}

function Get-QueueCount($name) {
  $q = docker compose exec -T rabbitmq rabbitmqctl list_queues -p health name messages
  foreach ($l in $q) {
    $p = $l -split "\s+"
    if ($p[0] -eq $name) { return [int]$p[1] }
  }
  return -1
}

$pwMedico   = if ($env:E2E_MEDICO_PW)   { $env:E2E_MEDICO_PW }   else { "medico123" }
$pwPaciente = if ($env:E2E_PACIENTE_PW) { $env:E2E_PACIENTE_PW } else { "paciente123" }
$pwAdmin    = if ($env:E2E_ADMIN_PW)    { $env:E2E_ADMIN_PW }    else { "admin123" }

Write-Host "== Correlation ID desta execucao: $cid ==`n"

# 0. Preparacao
docker compose exec -T rabbitmq rabbitmqctl purge_queue -p health notification.consultas.dlq | Out-Null

# 1. Login
$medico = Get-Token "medico" $pwMedico
$paciente = Get-Token "paciente" $pwPaciente
$admin = Get-Token "admin" $pwAdmin
Check "Login com os 3 papeis" ($medico -and $paciente -and $admin)

# 2. Fluxo completo
docker compose stop notification-consumer | Out-Null
$h = @{ Authorization = "Bearer $medico"; "X-Correlation-ID" = $cid }
$pac = "e2e-paciente-$cid"
$dia = Get-Random -Minimum 1 -Maximum 28
$hora = Get-Random -Minimum 8 -Maximum 18

$r1 = Invoke-WebRequest -Method Post -Uri "$base/api/medical-record/v1/pacientes/$pac/registros" -Headers $h `
  -ContentType "application/json" -UseBasicParsing `
  -Body '{"profissional_id":"medico-001","tipo":"anotacao","descricao":"registro do e2e"}'
Check "Medico cria prontuario (201)" ($r1.StatusCode -eq 201)

$body = "{`"paciente_id`":`"$pac`",`"profissional_id`":`"e2e-medico-$cid`",`"data_hora`":`"2033-01-$('{0:00}' -f $dia)T$('{0:00}' -f $hora):00:00Z`"}"
$r2 = Invoke-WebRequest -Method Post -Uri "$base/api/scheduling/v1/consultas" -Headers $h `
  -ContentType "application/json" -UseBasicParsing -Body $body
Check "Medico agenda consulta (201)" ($r2.StatusCode -eq 201)

Check "Evento na fila (consumidor parado)" ((Get-QueueCount "notification.consultas") -ge 1)

docker compose start notification-consumer | Out-Null
Start-Sleep -Seconds 10
Check "Fila consumida (0 mensagens)" ((Get-QueueCount "notification.consultas") -eq 0)
Check "DLQ vazia" ((Get-QueueCount "notification.consultas.dlq") -eq 0)

$pront = "$base/api/medical-record/v1/pacientes/$pac/registros"
Check "Medico le prontuario (200)" ((Get-Status $pront $medico) -eq 200)

# 3. Acessos negados
Check "Sem token -> 401" ((Get-Status $pront $null) -eq 401)
Check "Token invalido -> 401" ((Get-Status $pront "abc.def.ghi") -eq 401)
Check "Paciente no prontuario -> 403" ((Get-Status $pront $paciente) -eq 403)
Check "Admin no prontuario -> 403" ((Get-Status $pront $admin) -eq 403)
Check "Paciente DELETE em scheduling -> 403" ((Get-Status "$base/api/scheduling/v1/consultas/00000000-0000-0000-0000-000000000000/cancelamento" $paciente "DELETE") -eq 403)

# 4. Correlation ID nos logs
foreach ($svc in @("middleware", "scheduling", "medical-record", "notification-consumer")) {
  $achou = (docker compose logs $svc 2>&1 | Select-String $cid -Quiet)
  Check "Correlation ID presente nos logs de $svc" $achou
}

Write-Host ""
if ($falhas -eq 0) { Write-Host "Todos os passos passaram." -ForegroundColor Green; exit 0 }
else { Write-Host "$falhas passo(s) falharam." -ForegroundColor Red; exit 1 }