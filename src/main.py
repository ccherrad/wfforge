import uvicorn
from fastapi import FastAPI
from .config import settings
from .workflows.router import router as workflows_router

app = FastAPI(
    title="WFForge - Workflow Engine",
    description="A powerful workflow engine with FastAPI, Celery, and SQLite",
    version="0.1.0"
)

app.include_router(workflows_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "WFForge Workflow Engine API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )