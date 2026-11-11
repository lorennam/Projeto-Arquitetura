from fastapi import FastAPI

from auth.router import router as auth_router

app = FastAPI(
    title="Health Middleware",
    description="Middleware distribuído para integração de serviços de saúde",
    version="0.1.0"
)

app.include_router(auth_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "middleware"
    }