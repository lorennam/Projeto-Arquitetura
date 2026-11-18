"""Servidor gRPC do medical-record (chamadas internas serviço -> serviço)."""
import logging
import os

import grpc

import correlation
import prontuario_pb2
import prontuario_pb2_grpc
from repository import repositorio

logger = logging.getLogger("grpc")

GRPC_PORT = os.getenv("GRPC_PORT", "50051")
# Metadata gRPC é sempre minúscula.
CORRELATION_METADATA_KEY = correlation.HEADER.lower()


class ProntuarioService(prontuario_pb2_grpc.ProntuarioServiceServicer):
    async def ExisteProntuario(self, request, context):
        metadata = dict(context.invocation_metadata())
        cid = metadata.get(CORRELATION_METADATA_KEY) or correlation.gerar()
        token = correlation.definir(cid)
        try:
            existe = len(repositorio.listar(request.paciente_id)) > 0
            logger.info(
                "chamada gRPC concluída",
                extra={"method": "ExisteProntuario", "existe": existe},
            )
            return prontuario_pb2.ProntuarioResponse(existe=existe)
        finally:
            correlation.resetar(token)


async def iniciar_grpc() -> grpc.aio.Server:
    server = grpc.aio.server()
    prontuario_pb2_grpc.add_ProntuarioServiceServicer_to_server(
        ProntuarioService(), server
    )
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    await server.start()
    logger.info("servidor gRPC iniciado", extra={"port": GRPC_PORT})
    return server