FROM python:3.12-slim

WORKDIR /app

COPY services/scheduling/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Contrato gRPC compartilhado (proto/ na raiz): o código Python é gerado no build.
COPY proto/ /tmp/proto/
RUN python -m grpc_tools.protoc -I /tmp/proto \
    --python_out=. --grpc_python_out=. /tmp/proto/prontuario.proto

COPY services/scheduling/app/ .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]