#!/usr/bin/env bash
# Demonstra a resiliência do gateway derrubando um serviço ao vivo.
set -u

URL="http://localhost:8000/api/scheduling/health"
SERVICE="scheduling"

chamar() {
  local inicio fim codigo
  inicio=$(date +%s.%N)
  codigo=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
  fim=$(date +%s.%N)
  LC_ALL=C printf "  -> HTTP %s em %.2fs\n" "$codigo" "$(echo "$fim - $inicio" | bc)"
}

echo "1) Serviço saudável"
chamar

echo "2) Derrubando o container '$SERVICE'"
docker compose stop "$SERVICE" > /dev/null

echo "3) Chamadas com o serviço fora (timeout + retry; o circuito abre na 3ª)"
for i in 1 2 3; do chamar; done

echo "4) Circuito aberto: resposta imediata (fallback)"
chamar

echo "5) Subindo o container de volta"
docker compose start "$SERVICE" > /dev/null
echo "   aguardando a recuperação do circuito (12s)..."
sleep 12

echo "6) Serviço recuperado"
chamar