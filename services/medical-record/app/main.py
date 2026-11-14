from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator



app = FastAPI(
    title="Medical Record Service",
    description="Serviço de gerenciamento de prontuários médicos",
    version="0.1.0"
)
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "medical-record"
    }