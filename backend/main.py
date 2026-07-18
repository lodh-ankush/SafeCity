"""
SafeCity AI – FastAPI Backend
Real-Time Urban Safety Intelligence Platform
"""
import sys
import os

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.routes import router
from core.db import init_db
from core.ws_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="SafeCity AI",
    description="Real-Time Urban Safety Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Push newly-ingested incidents to connected clients in real time.
    Incidents are sent by api.routes.ingest_event() via the shared
    ConnectionManager whenever POST /api/ingest accepts a new incident;
    this handler just keeps the connection open until the client disconnects.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.get("/")
def root():
    return {
        "name": "SafeCity AI",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
