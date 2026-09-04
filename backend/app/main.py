import os
import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.config import BASE_DIR
from backend.app.database import init_db
from backend.app.routes import (
    auth_routes, farmer_routes, official_routes, admin_routes, public_routes
)
from backend.app.websocket_manager import manager
from backend.app.c_bridge import _load_c_library
from backend.app.cpp_bridge import _load_cpp_library

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sih_procurement")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SIH 2026 Procurement Platform...")
    init_db()
    _load_c_library()
    _load_cpp_library()
    logger.info("Backend services, PostgreSQL, C and C++ native modules ready.")
    yield
    logger.info("Shutting down SIH 2026 Procurement Platform...")

app = FastAPI(
    title="Digital System for Procurement Schedules, Farmer Queues and Real-Time Status",
    description="Smart India Hackathon 2026 - PS ID: 26032 Production Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Route Handlers
app.include_router(auth_routes.router)
app.include_router(farmer_routes.router)
app.include_router(official_routes.router)
app.include_router(admin_routes.router)
app.include_router(public_routes.router)

# Real-Time WebSocket Endpoint
@app.websocket("/ws/live")
async def websocket_live_queue(
    websocket: WebSocket,
    center_id: int = Query(default=1),
    user_id: int = Query(default=None)
):
    """
    Bi-directional WebSocket for real-time live queue tracking:
    Transmits instant token advancements, delay alerts, and turn arrivals without page reloads.
    """
    await manager.connect(websocket, user_id=user_id, center_id=center_id)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "event": "CONNECTED",
            "center_id": center_id,
            "message": f"Connected to live queue updates for Center {center_id}"
        })
        while True:
            data = await websocket.receive_text()
            # Client heartbeat or client request
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id=user_id, center_id=center_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id=user_id, center_id=center_id)

# Serve Static Frontend Assets
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    @app.get("/index.html")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/farmer")
    @app.get("/farmer.html")
    def serve_farmer():
        return FileResponse(FRONTEND_DIR / "farmer.html")

    @app.get("/official")
    @app.get("/official.html")
    def serve_official():
        return FileResponse(FRONTEND_DIR / "official.html")

    @app.get("/admin")
    @app.get("/admin.html")
    def serve_admin():
        return FileResponse(FRONTEND_DIR / "admin.html")
