# Demo ao vivo - Middleware Distribuido (Saude)
# Uso: powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
# Somente ASCII nos textos (PowerShell 5.1). Pausa a cada etapa.
$ErrorActionPreference = "Continue"
$base = "http://localhost:8000"
$cid  = "demo-ao-vivo"

$pwMedico   = if ($env:E2E_MEDICO_PW)   { $env:E2E_MEDICO_PW }   else { "medico123" }
$pwPaciente = if ($env:E2E_PACIENTE_PW) { $env:E2E_PACIENTE_PW } else { "paciente123" }

function Titulo($t) {
  Write-Host ""
  Write-Host "=================================================" -ForegroundColor Cyan
  Write-Host "  $t" -ForegroundColor Cyan
  Write-Host "=================================================" -ForegroundColor Cyan
}

function Pausa { Read-Host "[Enter para continuar]" | Out-Null }

function Get-Token($u, $p) {
  (Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType "application/json" `
    -Body "{`"username`":`"$u`",`"password`":`"$p`"}").access_token
}

# Retorna o status HTTP e o tempo gasto; mostra Retry-After quando existir
function Chamar($rotulo, $url, $token, $metodo = "GET") {
  $headers = @{ "X-Correlation-ID" = $cid }
  if ($token) { $headers["Authorization"] = "Bearer $token" }
  $ini = Get-Date
  $retry = ""
  try {
    $r = Invoke-WebRequest -Method $metodo -Uri $url -Headers $headers -UseBasicParsing
    $code = [int]$r.StatusCode
  } catch {
    $code = [int]$_.Exception.Response.StatusCode
    $ra = $_.Exception.Response.Headers["Retry-After"]
    if ($ra) { $retry = "  Retry-After: $ra" }
  }
  $seg = [math]::Round(((Get-Date) - $ini).TotalSeconds, 1)
  $cor = if ($code -ge 200 -and $code -lt 300) { "Green" } else { "Yellow" }
  Write-Host ("{0} -> {1}  ({2}s){3}" -f $rotulo, $code, $seg, $retry) -ForegroundColor $cor
  return $code
}

function Count-Fila {
  docker compose exec -T rabbitmq rabbitmqctl list_queues -p health name messages
}

$agend = "$base/api/scheduling/v1/consultas"
$pac   = "demo-paciente"
$pront = "$base/api/medical-record/v1/pacientes/$pac/registros"

# ---------------------------------------------------------------
Titulo "ETAPA 1 - Subir a stack e ver os containers (Arthur)"
docker compose up -d
docker compose ps
Pausa

# ---------------------------------------------------------------
Titulo "ETAPA 2 - Login e acessos negados 401/403 (Bento)"
$medico   = Get-Token "medico" $pwMedico
$paciente = Get-Token "paciente" $pwPaciente
Write-Host "Tokens obtidos (medico: $($medico.Length) chars, paciente: $($paciente.Length) chars)" -ForegroundColor Green
Chamar "Sem token           GET prontuario" $pront $null | Out-Null
Chamar "Paciente            GET prontuario" $pront $paciente | Out-Null
Chamar "Medico              GET prontuario" $pront $medico | Out-Null
Pausa

# ---------------------------------------------------------------
Titulo "ETAPA 3 - Fluxo completo: agendar, fila, notificacao (Lorenna e Lucas)"
Write-Host "Parando o consumidor para mostrar a mensagem na fila..." -ForegroundColor Gray
docker compose stop notification-consumer | Out-Null

$h = @{ Authorization = "Bearer $medico"; "X-Correlation-ID" = $cid }
Invoke-WebRequest -Method Post -Uri $pront -Headers $h -ContentType "application/json" -UseBasicParsing `
  -Body '{"profissional_id":"medico-001","tipo":"anotacao","descricao":"registro da demo"}' | Out-Null
Write-Host "Prontuario criado (201)" -ForegroundColor Green

$dia  = Get-Random -Minimum 1 -Maximum 28
$hora = Get-Random -Minimum 8 -Maximum 18
$body = "{`"paciente_id`":`"$pac`",`"profissional_id`":`"demo-medico`",`"data_hora`":`"2034-02-$('{0:00}' -f $dia)T$('{0:00}' -f $hora):00:00Z`"}"
$r = Invoke-WebRequest -Method Post -Uri $agend -Headers $h -ContentType "application/json" -UseBasicParsing -Body $body
Write-Host "Consulta agendada ($($r.StatusCode))" -ForegroundColor Green

Write-Host "`nFila com o consumidor parado (esperado: notification.consultas = 1):"
Count-Fila
Pausa

Write-Host "Religando o consumidor..." -ForegroundColor Gray
docker compose start notification-consumer | Out-Null
Start-Sleep -Seconds 6
docker compose logs notification-consumer --tail 5
Write-Host "`nFila depois (esperado: 0 na fila e 0 na DLQ):"
Count-Fila
Pausa

# ---------------------------------------------------------------
Titulo "ETAPA 4 - Correlation ID e trace no Jaeger (Arthur)"
Write-Host "Correlation ID desta demo: $cid"
Write-Host "Abra o Jaeger: http://localhost:16686  (Service: middleware -> Find Traces -> POST /api/{service}/{path} mais recente)"
Write-Host "Plano B (logs): docker compose logs middleware scheduling medical-record notification-consumer 2>&1 | Select-String $cid"
Pausa

# ---------------------------------------------------------------
Titulo "ETAPA 5 - Derrubar o scheduling e ver o circuit breaker (Anna)"
docker compose stop scheduling | Out-Null
Write-Host "scheduling PARADO. Cada chamada tenta 4 vezes (1 + 3 retries) com backoff 0,5/1/2 s: ~11,6 s." -ForegroundColor Gray
Chamar "Chamada 1 (retry+backoff)" $agend $medico | Out-Null
Chamar "Chamada 2" $agend $medico | Out-Null
Chamar "Chamada 3 (abre o circuito)" $agend $medico | Out-Null
Write-Host "`nAgora o circuito esta ABERTO: resposta imediata." -ForegroundColor Gray
Chamar "Chamada 4 (fail fast)" $agend $medico | Out-Null

Write-Host "Religando o scheduling e testando a recuperacao (half-open apos 10 s)..." -ForegroundColor Gray
docker compose start scheduling | Out-Null
for ($i = 1; $i -le 15; $i++) {
  Start-Sleep -Seconds 3
  $c = Chamar "Tentativa $i" $agend $medico
  if ($c -eq 200) { Write-Host "RECUPERADO: circuito fechou, sistema respondendo." -ForegroundColor Green; break }
}
Pausa

# ---------------------------------------------------------------
Titulo "ETAPA 6 - Grafana (Arthur)"
Write-Host "Abra http://localhost:3000 e mostre o dashboard (picos de latencia/erros durante a queda)."
Write-Host ""
Write-Host "Fim da demo." -ForegroundColor Green