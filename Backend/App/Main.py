"""
FastAPI application factory.
YouTube RAG Chatbot — Core API server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from App.Routes.chat import router as chat_router
from App.Routes.quiz import router as quiz_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("=" * 60)
    print("  YouTube RAG Chatbot — Starting Up")
    print("=" * 60)

    # Pre-initialize heavy services on startup
    from App.Services.vectorstore import VectorStoreService
    VectorStoreService()

    from App.Services.agent import get_graph
    get_graph()

    print("=" * 60)
    print("  ✓ All services initialized. Server ready!")
    print("  → API docs: http://localhost:8000/docs")
    print("  → Frontend: http://localhost:8000")
    print("=" * 60)

    yield

    print("[Shutdown] Cleaning up...")


# Create the FastAPI app
app = FastAPI(
    title="YouTube RAG Chatbot",
    description="AI-powered YouTube video Q&A with timestamp-referenced answers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (allow frontend dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(chat_router)
app.include_router(quiz_router)

# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "Frontend")
frontend_dir = os.path.abspath(frontend_dir)

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        """Serve the main frontend page."""
        index_path = os.path.join(frontend_dir, "index.html")
        return FileResponse(index_path)
else:
    @app.get("/")
    async def root():
        return {
            "message": "YouTube RAG Chatbot API",
            "docs": "/docs",
            "status": "running",
        }
