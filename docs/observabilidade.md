# Observabilidade: logs JSON e métricas

Os quatro serviços (`middleware`, `scheduling`, `medical-record` e `notification`) seguem o mesmo padrão de logs estruturados e métricas Prometheus.

## Estrutura

Cada serviço tem quatro módulos em `app/`, copiados entre os serviços. Cada container só copia a própria pasta `app/`, e os serviços só se falam pela rede, então não há código compartilhado.

| Arquivo | Responsabilidade |
| --- | --- |
| `logging_json.py` | Formatter JSON e configuração do `logging` |
| `correlation.py` | Contexto do `correlation_id` da requisição |
| `metrics.py` | Definição das métricas Prometheus |
| `observability.py` | Middleware HTTP (log + métricas) e endpoint `/metrics` |

O `main.py` de cada serviço só importa e chama `configurar_observabilidade(app, "<serviço>")`.

No `middleware`, o `correlation.py` é um adaptador fino sobre `gateway/correlation.py`. Assim existe um único `correlation_id` por requisição, o do gateway.

## Logs

Uma linha JSON por requisição, na saída padrão:

```json
{"timestamp": "2026-11-16T16:11:58+00:00", "level": "WARNING", "service": "middleware",
 "message": "requisição concluída", "correlation_id": "31a255dd-...", "method": "GET",
 "path": "/nada", "status": 401, "duration_ms": 0.31}
```

- Nível: `INFO` (status < 400), `WARNING` (4xx) e `ERROR` (5xx ou exceção, com stack trace).
- `/health` e `/metrics` não geram log, para o healthcheck e o scrape não poluírem a saída.
- O nível mínimo vem da variável `LOG_LEVEL` (padrão `INFO`).

## correlation_id

- Header: `X-Correlation-ID`.
- O gateway gera o id (UUID) quando o cliente não envia, e repassa aos serviços.
- Se um serviço receber a requisição sem o header, ele gera um UUID.
- O valor é devolvido no mesmo header da resposta e aparece em todos os logs da requisição.
- No middleware, os 401 e 403 de JWT/RBAC também saem com o id, porque o log fica por fora deles.

## Métricas

`GET /metrics` em cada serviço, no formato de texto do Prometheus.

| Métrica | Tipo | Rótulos |
| --- | --- | --- |
| `http_requests_total` | Counter | `service`, `method`, `route`, `status` |
| `http_request_duration_seconds` | Histogram | `service`, `method`, `route` |
| `http_errors_total` | Counter | `service`, `method`, `route`, `status` (só 5xx) |

- `route` é o modelo da rota (`/v1/pacientes/{paciente_id}/registros`), nunca o caminho real. Senão cada UUID criaria uma série nova.
- Requisições que não casam com nenhuma rota usam `route="nao_mapeada"`. No middleware, rotas inexistentes caem aqui com status `401`, porque o JWT barra antes da rota ser resolvida.
- `/health` e `/metrics` não entram na contagem.

### Portas de scrape

| Serviço | Endereço interno |
| --- | --- |
| middleware | `middleware:8000/metrics` |
| scheduling | `scheduling:8001/metrics` |
| medical-record | `medical-record:8002/metrics` |
| notification | `notification:8003/metrics` |

No middleware, o `/metrics` está na allowlist de rotas públicas (`auth/public_routes.py`), senão o JWT responderia 401 ao Prometheus. As métricas só têm contagens e latências, sem dados de usuário.

## Limitações

- Só o lado HTTP do `notification` está coberto. O consumidor do RabbitMQ não propaga `correlation_id` nas mensagens, o que fica como evolução.
- O `middleware` e o `notification` não têm testes de observabilidade. O `scheduling` e o `medical-record` têm.