import os
import uvicorn
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from backend.database.db import init_db
from backend.api.routes_analyze import router as analyze_router
from backend.api.routes_privacy import router as privacy_router
from backend.api.routes_admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    try:
        init_db()
        print("Auriic ATS Checker Database Initialized.")
    except Exception as e:
        print(f"Lifespan init_db notice: {e}")
    yield

app = FastAPI(
    title="Auriic Free ATS Resume Checker API",
    description="100% Deterministic ATS Scoring Engine & Compliant Lead Generation for Auriic Services",
    version="1.0.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": str(exc),
            "type": type(exc).__name__,
        }
    )

# CORS middleware for development and production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://ats.auriic.co",
        "https://auriic.co",
        "https://auriic-ats-tool.vercel.app"
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(analyze_router)
app.include_router(privacy_router)
app.include_router(admin_router)

@app.get("/api/health")
async def health_check():
    from backend.database.db import IS_POSTGRES, DATABASE_URL, query_one
    db_type = "postgres" if IS_POSTGRES else "sqlite"
    db_connected = False
    db_error = None
    leads_count = 0
    submissions_count = 0
    try:
        row = query_one("SELECT count(*) as count FROM ats_leads")
        if row:
            leads_count = row.get("count", 0)
        sub_row = query_one("SELECT count(*) as count FROM ats_submissions")
        if sub_row:
            submissions_count = sub_row.get("count", 0)
        db_connected = True
    except Exception as e:
        db_error = str(e)

    return {
        "status": "healthy",
        "service": "Auriic Free ATS Resume Checker",
        "scoring_version": "1.0.0",
        "engine": "Deterministic-Rule-Based",
        "database": {
            "type": db_type,
            "has_database_url": bool(DATABASE_URL),
            "connected": db_connected,
            "leads_count": leads_count,
            "submissions_count": submissions_count,
            "error": db_error,
        }
    }

# Production: Serve React Frontend SPA if built
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return None
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend build not found"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
