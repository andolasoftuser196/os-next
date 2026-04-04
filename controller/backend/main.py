"""
Dev Controller — FastAPI Backend
Manages dynamic V4/selfhosted instances, container status, logs, and web terminal.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routes import instances, database, monitoring, websockets

app = FastAPI(
    title="Dev Controller",
    version="1.0.0",
    description="Manages dynamic OrangeScrum V4/selfhosted instances — containers, databases, routing, and git worktrees.",
)

# ─── CORS — restrict to same origin ─────────────────────────────────────────

domain = os.environ.get("DOMAIN", "")
allowed_origins = [f"https://control.{domain}", f"http://control.{domain}"] if domain else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ─── Include Routers ─────────────────────────────────────────────────────────

app.include_router(instances.router)
app.include_router(database.router)
app.include_router(monitoring.router)
app.include_router(websockets.router)

# ─── Serve Frontend ──────────────────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = (FRONTEND_DIR / full_path).resolve()
        if not str(file_path).startswith(str(FRONTEND_DIR.resolve())):
            return FileResponse(FRONTEND_DIR / "index.html")
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
