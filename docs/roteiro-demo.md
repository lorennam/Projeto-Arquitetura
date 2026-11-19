# Roteiro da demo ao vivo (4 a 5 min)

Projeto Middleware Distribuído (Saúde), Sistemas Distribuídos, UNICAP.
Comandos em PowerShell, na raiz do repositório. Alvo da demo: **4:40** (20 s de folga).

> **Verificado no código/saídas:** `X-User-*` é descartado no gateway; retry vale para qualquer método (inclusive POST); breaker conta 1 falha por requisição que esgotou os retries; `GET /api/scheduling/v1/consultas` com token de médico devolve 200; serviços no Jaeger: `middleware`, `scheduling`, `medical-record`.
>
> **Atenção:** o 4º serviço (`patient-extra-point`, 8004, CRUD de pacientes em Postgres) falta no README e no relatório; os trechos prontos estão em `docs/patient-extra-point-trechos.md`. Dashboard do Grafana: **Middleware Saude - Visao Geral** (importar `docs/grafana-dashboard.json`).

---

## 1. Roteiro minutado

Terminal com fonte grande. O script `scripts/demo.ps1` faz as etapas de terminal com pausa a cada uma; a coluna "Digitar" é o que ele executa (ou o que digitar à mão). Jaeger, `/docs` e Grafana são abas do navegador já abertas.

| # | Tempo | Quem | Digitar / clicar | Deve aparecer | Falar (1-2 frases) |
|---|---|---|---|---|---|
| 1 | 0:00-0:20 (20 s) | Arthur | `docker compose up -d` e `docker compose ps` | Tudo `Up`/`healthy` (consumer só `Up`) | "Toda a stack sobe com um comando: gateway, 4 serviços de negócio, RabbitMQ e a observabilidade. Só o middleware é exposto ao host, na 8000." |
| 2 | 0:20-0:55 (35 s) | Bento | Login (médico, paciente); `GET` no prontuário: sem token, paciente, médico | `401`, `403`, `200` | "401 é 'não sei quem é você', 403 é 'sei quem é, mas o papel não permite'. O prontuário só aceita `doctor`." |
| 3 | 0:55-1:55 (60 s) | Lorenna (agendar/prontuário) + Lucas (fila) | Parar consumer; criar prontuário e agendar (`201`); `list_queues` (=1); religar consumer; `list_queues` (=0) | `notification.consultas` 1 e depois 0; DLQ 0 | Lorenna: "O scheduling consulta o prontuário por gRPC, com timeout de 2 s, sem bloquear o agendamento." Lucas: "Publica `consulta.agendada` no RabbitMQ; o consumidor tem retry, DLQ e idempotência por `message_id`." |
| 4 | 1:55-2:20 (25 s) | **Bento** | Aba do Jaeger: Service `middleware` → Find Traces → abrir o `POST /api/{service}/{path}` mais recente | Trace com 3 serviços (~13 spans) | "O mesmo `X-Correlation-ID` aparece nos logs de 4 origens e vira um trace no Jaeger: gateway, scheduling e medical-record na mesma requisição." |
| 5 | 2:20-2:45 (25 s) | **Arthur** | **Nova aba:** `http://localhost:8000/docs`. Fazer login (`POST /auth/login`), autorizar com o token e executar o `GET` de pacientes do `patient-extra-point` (confirmar o nome exato da rota no ensaio) | `200` com a lista de pacientes | "Este é o nosso 4º serviço: um CRUD de pacientes com Postgres, CPF único, também atrás do gateway. Mesmo JWT, mesmo RBAC, mesma observabilidade. O `/docs` mostra todas as rotas do middleware." |
| 6 | 2:45-4:15 (90 s) | Anna | Ver seção 2 | 504, 504, 504, depois 503 imediato com `Retry-After: 10`; depois 200 | Ver seção 2 |
| 7 | 4:15-4:40 (25 s) | Arthur | Aba do Grafana: dashboard "Middleware Saude - Visao Geral" | Picos de 5xx e de latência durante a queda | "Prometheus coleta e o Grafana mostra o impacto da queda que acabamos de provocar." |

**O que foi cortado (e por quê):** demonstração da DLQ (mensagem venenosa), rotas v1/v2, queda do RabbitMQ (limitação conhecida, ver plano B/pergunta 3), `Select-String` nos logs (substituído pelo Jaeger; fica como plano B), `e2e.ps1` (17 passos, longo demais; só citar que existe) e `/test/latency` (explicar só se perguntarem). Para abrir espaço para a etapa 5, as etapas 1, 2, 3, 4 e 7 perderam 5 s cada e a 6 perdeu 5 s.

---

## 2. Plano de derrubar o container (etapa 6, Anna)

**Serviço:** `scheduling`. Não derrubar RabbitMQ ao vivo.

**Sequência (simplificada):**

1. `docker compose stop scheduling`.
2. Chamar 3 vezes `GET /api/scheduling/v1/consultas` (token de médico). Cada uma devolve **504 em ~11,6 s**.
   - *Falar durante a espera (uma frase só):* "Cada chamada tenta 3 vezes com backoff e desiste com 504. Cada falha conta no circuit breaker."
3. 4ª chamada: **503 imediato** com `Retry-After: 10`.
   - *Falar:* "Na terceira falha o circuito abriu: agora o gateway falha rápido, sem esperar timeout."
4. `docker compose start scheduling` **logo depois do 503** e chamar a cada 3 s até dar **200**.
   - *Falar:* "Depois de 10 s o breaker testa o serviço (half-open): um sucesso fecha o circuito."

**Por que não pausar antes de religar:** se esperarmos mais de 10 s depois do 503, o breaker já está half-open e o 503 perde o sentido. Ordem: 503 → religar → polling.

**Se o serviço ainda estiver subindo:** pode vir mais um 503 (o breaker reabre por 10 s). É esperado; a próxima tentativa dá 200.

**Para encurtar:** cortar a fala, não as falhas (são 3 até abrir).

**Opcional (+5 s):** uma chamada ao `medical-record` durante o 503 prova que o resto do sistema continua respondendo.

---

## 3. Checklist pré-demo

### 30 min antes
- [ ] Carregador na tomada, modo "não perturbe", fechar apps, notificações do Windows desligadas.
- [ ] `docker compose up --build -d` (o build precisa acontecer **agora**, não na apresentação).
- [ ] `docker compose ps`: tudo `healthy`; **confirmar que `notification` está `healthy`** (correção da rota `/health`) e que `patient-extra-point` e `patient-db` estão `healthy`. Consumer só precisa estar `Up`.
- [ ] `docker compose exec rabbitmq rabbitmqctl purge_queue -p health notification.consultas.dlq`
- [ ] `docker compose exec rabbitmq rabbitmqctl list_queues -p health name messages`: tudo 0.
- [ ] Rodar `powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1` uma vez: 17 passos OK.
- [ ] Rodar `scripts/demo.ps1` inteiro uma vez (ensaio) e confirmar que o `scheduling` voltou (`docker compose ps`).
- [ ] Abrir abas, **nesta ordem** (a ordem das abas segue a ordem da demo): Jaeger http://localhost:16686 → **Swagger do gateway http://localhost:8000/docs** → Grafana http://localhost:3000 (já logado, `GRAFANA_USER`/`GRAFANA_PASSWORD` do `.env`). Extras de apoio: RabbitMQ http://localhost:15672 (vhost `health`), Prometheus http://localhost:9090.
- [ ] Arthur: testar no `/docs` o login + o `GET` de pacientes uma vez antes e anotar a rota exata: ________.
- [ ] Gerar dados para o Grafana (painéis vazios = demo ruim): `1..15 | ForEach-Object { curl.exe -s "http://localhost:8000/test/latency?delay=$($_ % 4)" | Out-Null }` e rodar o `e2e.ps1`. Abrir o dashboard e anotar o nome aqui: ________.
- [ ] Se as senhas do `.env` forem diferentes: `$env:E2E_MEDICO_PW="..."` e `$env:E2E_PACIENTE_PW="..."` na sessão do PowerShell.
- [ ] Prints e vídeo de reserva gravados (seção 5).

### 5 min antes
- [ ] Terminal limpo (`Clear-Host`), fonte grande (≥ 18 pt), tema de alto contraste, na raiz do repositório.
- [ ] `docker compose ps` com tudo saudável; DLQ em 0 (purge de novo, por garantia).
- [ ] Ter gerado token novo é irrelevante: o `demo.ps1` já faz login na etapa 2 (token vale 30 min, então iniciem o script dentro dessa janela). Se for usar comandos manuais:
  ```powershell
  $t = (Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login -ContentType "application/json" -Body '{"username":"medico","password":"medico123"}').access_token
  $h = @{ Authorization = "Bearer $t" }
  ```
- [ ] Slides abertos no ponto da demo; modo apresentador; cronômetro visível para a pessoa que controla o tempo.
- [ ] Todos presentes (ausência = -0,5).
- [ ] Wi-Fi: não é necessário para a demo (tudo local); ter hotspot só por segurança.

---

## 4. Script opcional

`scripts/demo.ps1` (já criado): etapas de terminal com pausa por Enter, só ASCII. **Ajuste necessário:** o roteiro agora tem 7 etapas; as etapas 4 (Jaeger), 5 (`/docs`) e 7 (Grafana) são no navegador, então o script só precisa de uma pausa "Enter" no lugar de cada uma, para a equipe trocar de aba. Não colem blocos longos no terminal; rodem o arquivo.

Uso: `powershell -ExecutionPolicy Bypass -File scripts/demo.ps1`

---

## 5. Plano B

| Falha | Sintoma | Ação rápida |
|---|---|---|
| Docker lento | `up` demora | Já estar rodando; na demo, mostrar só `docker compose up -d` (instantâneo com tudo de pé) e `ps`. Se o Docker Desktop travar: reiniciar antes, nunca na hora. |
| Porta ocupada | `bind: address already in use` | `netstat -ano \| findstr :8000`, matar o processo; ou `docker compose down` e subir de novo. Checar no checklist de 30 min. |
| Token expirado | `401` onde deveria ser 200 | Rodar de novo a etapa de login; o `demo.ps1` já gera token novo. No `/docs`, refazer o Authorize. |
| Container `unhealthy` | `ps` com `unhealthy` | `docker compose restart <serviço>`; se `notification`, confirmar a rota `/health`; se `patient-extra-point`, conferir se o `patient-db` está saudável. Não iniciar a demo com serviço doente. |
| `/docs` falha ou pacientes dá erro | Swagger não carrega ou 5xx | Mostrar o print de reserva do `/docs` e falar do 4º serviço em 2 frases; seguir para a etapa 6. |
| Consulta duplicada/409 | 409 no agendamento | O script usa data aleatória; reexecutar. |
| Fila não esvazia | `notification.consultas` ≠ 0 | Aguardar mais 5 s; ver `docker compose logs notification-consumer --tail 20`. |
| `scheduling` demora a recuperar | 503 por mais de ~25 s | Normal se uma requisição em half-open pegou o serviço ainda subindo (o breaker reabre por 10 s). Aguardar mais 1 ou 2 tentativas. Se persistir: `docker compose ps` e `docker compose logs scheduling --tail 20`. |
| Jaeger/Grafana sem dado | Tela vazia | Mostrar o print de reserva; plano B de rastreio: `docker compose logs middleware scheduling medical-record notification-consumer 2>&1 \| Select-String demo-ao-vivo`. |
| Internet | (a demo é local) | Sem impacto. Só jwt.io precisa de internet: não usem. |
| Tudo falha | | Mostrar o **vídeo de reserva** da demo completa (gravar antes, 5 min, com cada etapa) e narrar por cima. |

**Reservas:** vídeo da demo completa + prints de: `ps` saudável, 401/403/200, fila 1 → 0, trace no Jaeger, `/docs` com o `GET` de pacientes em 200, 504 → 503 com `Retry-After`, 200 após recuperação, Grafana.

---

## 6. Divisão de fala (todos falam e todos dominam)

Apresentação total: 10 a 15 min. Alvo de **13 min** (2 min de folga para o professor/perguntas).

| Bloco | Tempo | Quem |
|---|---|---|
| Contexto (domínio Saúde, problema, objetivo) | 1:30 | Lorenna |
| Arquitetura | 3:30 | Arthur (visão geral, Docker, observabilidade, 1 min) → Anna (gateway/resiliência, 1:15) → Bento (JWT/RBAC, 45 s) → Lucas (mensageria, 30 s) |
| Demo | 4:40 | Etapa 1: Arthur (teclado) · 2: Bento · 3: Lorenna + Lucas · 4 (Jaeger): **Bento** · 5 (`/docs` + 4º serviço): **Arthur** · 6 (queda): Anna · 7 (Grafana): Arthur |
| Desafios e lições | 2:30 | 30 s cada: um desafio real de cada um da própria área |
| Perguntas | 5:00 | Quem tem a área responde; **qualquer um pode complementar** |

**Regra contra "só sabe a sua parte":** cada pessoa aprende 1 pergunta de outra área (da seção 7). Sugestão: Arthur ↔ Anna (resiliência), Bento ↔ Lorenna (contratos e RBAC), Lucas ↔ Arthur (observabilidade de fila). Como o Bento agora fala do Jaeger, ele também precisa saber a pergunta 12 e como o trace conecta os serviços. O professor pode perguntar a qualquer um.

---

## 7. Perguntas prováveis (12 + 2 extras do 4º serviço)

> Respostas baseadas no código, no `relatorio.md` e no `tolerancia-falhas.md`. A 12 usa só o que o código mostra (comentário em `main.py`); ajustem se alguém lembrar de outro motivo.

1. **Por que consistência eventual?**
   O agendamento não deve falhar porque a notificação ou o prontuário estão lentos. A consulta é gravada e o evento vai para a fila; a notificação acontece depois. Troca-se consistência imediata por disponibilidade e desacoplamento.

2. **Por que gRPC nessa chamada (scheduling → medical-record)?**
   Chamada interna, síncrona e frequente entre dois serviços que se conhecem. O contrato tipado em `proto/prontuario.proto` é a única fonte da verdade (código gerado no build), a serialização binária sobre HTTP/2 é mais leve que JSON e há timeout e metadata nativos (usamos para o correlation ID e o `traceparent`). Na borda mantivemos REST. A chamada é informativa: timeout de 2 s e, se falhar, o agendamento continua.

3. **O que acontece se o RabbitMQ cair?**
   Limitação conhecida e documentada: o `POST /consultas` fica preso no produtor (loop de reconexão), e o cliente pode receber 504 ou 409 mesmo com a consulta criada. Mitigação possível (trabalho futuro): publicar com outbox/ timeout de publicação. Eventos já na fila persistem no broker.

4. **Por que 401 e 403 são diferentes?**
   401: sem token, inválido ou expirado ("quem é você?"). 403: autenticado, mas o papel não tem permissão ("sei quem é, mas não pode").

5. **Como evitam forjar `X-User-Role`?**
   O papel vem do **JWT assinado (HS256)**, validado no gateway. O proxy copia os headers do cliente, mas `strip_internal_headers` remove **qualquer `X-User-*`** antes de o gateway injetar `X-User-Id`/`X-User-Role` a partir do token. Os serviços confiam nesses headers porque só o gateway é alcançável de fora (rede interna do Docker). Limitação assumida: sem mTLS entre serviços.

6. **Por que retry em POST é um risco?**
   O gateway repete qualquer método em falha de rede (`httpx.RequestError`), inclusive POST, sem chave de idempotência. Se o serviço processou mas a resposta se perdeu, o retry pode duplicar ou gerar conflito aparente. Já vimos isso: com o RabbitMQ fora, a consulta é criada e o cliente recebe `409`. Hoje a idempotência existe só no consumidor (`message_id`); a evolução é uma chave de idempotência no POST ou *transactional outbox*. Respostas HTTP 4xx/5xx do serviço **não** são repetidas.

7. **O que é half-open?**
   Estado intermediário do circuit breaker: depois de 10 s aberto, as requisições voltam a passar. Um sucesso fecha o breaker; uma falha o reabre por mais 10 s.

8. **Por que não usaram Kong (ou outro gateway pronto)?**
   O enunciado exige um middleware construído do zero e penaliza em -3,0 o uso de gateway pronto como solução principal. Implementamos nós mesmos roteamento, JWT, RBAC, correlation ID, timeout, retry e circuit breaker; usamos só bibliotecas auxiliares (FastAPI, httpx, clientes de fila).

9. **Por que o circuit breaker é por serviço?**
   Para isolar falhas: com o `scheduling` parado, o prontuário e o login continuam funcionando (degradação parcial, não total).

10. **Qual a diferença entre retry e circuit breaker?**
    Retry tenta de novo a mesma chamada para absorver falhas transitórias (backoff 0,5/1/2 s). O breaker para de tentar quando a falha é persistente, falhando rápido (503 + `Retry-After`) e protegendo o serviço e o cliente.

11. **O que é a DLQ e como a idempotência funciona?**
    Mensagens que falham são reenviadas (TTL 5 s, até 3 vezes) e depois vão para `notification.consultas.dlq`. A idempotência evita processar o mesmo `message_id` duas vezes (registro em SQLite).

12. **Para que serve a rota pública `/test/latency`?**
    É uma rota de teste para o Grafana: dorme `delay` segundos (máximo 5) e responde `ok`, gerando latência conhecida nas métricas sem precisar de token. Não acessa dados nem serviços. Está na allowlist de rotas públicas (`public_routes.py`), junto de `/health`, `/metrics`, `/auth/login` e docs. Em produção seria removida ou protegida. O Prometheus coleta as métricas e o Grafana as exibe.

13. **O que é o `patient-extra-point` e por que usa Postgres se os outros usam memória?**
    É o serviço de cadastro de pacientes (CRUD em `/v1/pacientes`, CPF único). Os demais serviços usam repositório em memória para focar no middleware; este tem banco relacional real, o que mostra o gateway roteando para um serviço com persistência e mais uma dependência. O `/health` verifica a conexão com o banco e o compose só o sobe depois que o `patient-db` está saudável. É o 4º serviço (bônus de mais de 3 serviços).

14. **Um paciente logado consegue ver os dados de outros pacientes?**
    Hoje sim: o papel `patient` tem `GET` no serviço e a listagem devolve todos os cadastros (inclusive CPF). A regra "paciente só vê o próprio cadastro" não foi implementada: exigiria filtrar por `X-User-Id` no serviço. Está registrada como limitação e como evolução (LGPD). Mesma lógica da limitação já documentada para o prontuário.

---

## 8. Ensaio cronometrado

Cronômetro (celular) em modo volta. Fazer 3 rodadas: 1ª lendo o roteiro, 2ª só com o script, 3ª simulando a banca (com interrupções e perguntas).

| Etapa | Tempo-alvo | Marca acumulada | Limite duro |
|---|---|---|---|
| 1. up/ps | 0:20 | 0:20 | 0:30 |
| 2. 401/403/200 | 0:35 | 0:55 | 1:05 |
| 3. fluxo completo | 1:00 | 1:55 | 2:10 |
| 4. Jaeger (Bento) | 0:25 | 2:20 | 2:35 |
| 5. `/docs` + 4º serviço (Arthur) | 0:25 | 2:45 | 3:00 |
| 6. queda e recuperação (Anna) | 1:30 | 4:15 | 4:30 |
| 7. Grafana | 0:25 | 4:40 | 5:00 |

**Passo a passo:**
1. Estado inicial: `docker compose ps` saudável, DLQ zerada, consumer `Up`.
2. Iniciar o cronômetro ao digitar o primeiro comando; anotar o tempo ao fim de cada etapa.
3. Se uma etapa passar do limite duro, **corte** o item opcional (Grafana vira print; Jaeger ou `/docs` viram uma frase).
4. Após cada rodada: `docker compose ps` (confirmar `scheduling` e `notification-consumer` de volta) e purge da DLQ.
5. Na rodada 3, o professor-simulado faz 3 perguntas aleatórias a pessoas **fora da área** delas.
6. Meta final: 3 rodadas seguidas dentro de 4:40 ± 20 s sem erro.
7. Última rodada completa deve ser **gravada** (vira vídeo de reserva).