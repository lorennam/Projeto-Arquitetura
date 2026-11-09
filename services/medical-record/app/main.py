from fastapi import FastAPI

app = FastAPI(
    title="Medical Record Service",
    description="Serviço de gerenciamento de prontuários médicos",
    version="0.1.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "medical-record"
    }