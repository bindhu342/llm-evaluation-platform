from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from backend.api.evaluation_routes import router as evaluation_router
from backend.database.database import init_db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="LLM Evaluation Platform",
    description="Multi-agent AI response evaluation platform using LLM-as-a-Judge.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server and any configured frontend origin
_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin, "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(evaluation_router)


@app.get("/")
def root():
    return {"message": "LLM Evaluation Platform API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
