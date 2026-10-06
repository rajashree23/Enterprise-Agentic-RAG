from fastapi import FastAPI

from agentic_rag.api.routes import router

app = FastAPI(title="Agentic RAG")

app.include_router(router)
