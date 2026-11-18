"""Cliente gRPC do scheduling (chamada interna ao medical-record)."""
import logging
import os
from typing import Optional

import grpc
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient

import correlation
import prontuario_pb2
import prontuario_pb2_grpc

logger = logging.getLogger("grpc")

MEDICAL_RECORD_GRPC_ADDR = os.getenv("MEDICAL_RECORD_GRPC_ADDR", "medical-record:50051")
GRPC_TIMEOUT_SECONDS = float(os.getenv("GRPC_TIMEOUT_SECONDS", "2"))

# Instrumenta o cliente gRPC antes de criar o canal: cria o span de cliente
# e injeta o traceparent na metadata.
GrpcInstrumentorClient().instrument()

_channel = grpc.insecure_channel(MEDICAL_RECORD_GRPC_ADDR)
_stub = prontuario_pb2_grpc.ProntuarioServiceStub(_channel)


def paciente_tem_prontuario(paciente_id: str, correlation_id: str) -> Optional[bool]:
    """Pergunta ao medical-record se o paciente tem prontuário.

    Retorna True/False, ou None se o serviço não respondeu. Não levanta
    exceção: a falha do gRPC não deve impedir o agendamento.
    """
    try:
        resposta = _stub.ExisteProntuario(
            prontuario_pb2.ProntuarioRequest(paciente_id=paciente_id),
            timeout=GRPC_TIMEOUT_SECONDS,
            # Metadata gRPC é sempre minúscula.
            metadata=((correlation.HEADER.lower(), correlation_id),),
        )
        logger.info(
            "chamada gRPC ao medical-record concluída",
            extra={"method": "ExisteProntuario", "existe": resposta.existe},
        )
        return resposta.existe
    except grpc.RpcError as erro:
        logger.warning(
            "chamada gRPC ao medical-record falhou",
            extra={"method": "ExisteProntuario", "grpc_status": str(erro.code())},
        )
        return None