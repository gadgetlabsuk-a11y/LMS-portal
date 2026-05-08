"""
FastAPI main application file.
Sets up the FastAPI app with all routers, middleware, and startup tasks.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import asyncio
import logging
import uuid
from datetime import datetime, timezone

# Import config and database
from config import settings
from database import init_db, get_db
from models import User, UserRole, WhiteLabelConfig, FeatureFlag, ErrorLog
from services.auth_service import AuthService

# Import routers
from routers import admin, auth, users, courses, security, dev_tools, whitelabel, learn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup then shutdown."""
    # --- STARTUP ---
    logger.info("Starting LMS Course Builder API")

    # Increase the default thread pool so sync `def` route handlers can serve
    # many concurrent requests without queuing behind each other.
    # FastAPI dispatches every sync handler via run_in_executor(None, …) which
    # uses this pool.  Default is min(32, cpu_count+4) — too small for load
    # tests.  20 threads pairs well with pool_size=10/max_overflow=10 on the DB.
    _executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="lms")
    asyncio.get_running_loop().set_default_executor(_executor)
    logger.info("Default thread-pool executor set to 20 workers")

    try:
        init_db()
        logger.info("Database initialized")

        db = next(get_db())

        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            hashed_password = AuthService.hash_password("LMSadmin2026!")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            logger.info("Default admin user created (username: admin) — change the password immediately")

        config = db.query(WhiteLabelConfig).first()
        if not config:
            config = WhiteLabelConfig(
                brand_name="LMS Course Builder",
                primary_color="#1F2937",
                secondary_color="#6366F1",
                accent_color="#F59E0B",
                bg_color="#FFFFFF",
                text_color="#1F2937",
                font_family="Inter, system-ui, sans-serif",
                heading_font="Poppins, system-ui, sans-serif",
                border_radius="0.5rem",
                button_style="rounded",
            )
            db.add(config)
            db.commit()
            logger.info("Default white label config created")

        default_flags = [
            ("course_generation", True, "Enable Claude-powered course generation"),
            ("advanced_analytics", False, "Enable advanced analytics features"),
            ("bulk_import", True, "Enable bulk user import"),
            ("mfa_required", False, "Require MFA for all users"),
        ]

        for flag_name, enabled, description in default_flags:
            flag = db.query(FeatureFlag).filter(FeatureFlag.name == flag_name).first()
            if not flag:
                flag = FeatureFlag(name=flag_name, enabled=enabled, description=description)
                db.add(flag)

        db.commit()
        logger.info("Default feature flags created")

    except Exception as e:
        logger.error(f"Startup error: {str(e)}", exc_info=True)
        raise

    yield  # App is running

    # --- SHUTDOWN ---
    _executor.shutdown(wait=False)
    logger.info("Shutting down LMS Course Builder API")


# Create FastAPI app
app = FastAPI(
    title="LMS Course Builder API",
    description="Backend API for LMS Course Builder with admin features",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
# Note: allow_credentials=True is incompatible with allow_origins=["*"].
# Set CORS_ORIGINS in your .env to restrict to specific origins in production.
# e.g. CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]
_FRONTEND_ORIGIN = "http://dta9d9jm5k5tb94wnomxfxps.188.245.67.238.sslip.io"
_cors_origins = (
    settings.CORS_ORIGINS
    if settings.CORS_ORIGINS != ["*"]
    else [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        _FRONTEND_ORIGIN,  # standalone frontend Coolify deployment
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that logs all errors.

    Args:
        request: HTTP request
        exc: Exception

    Returns:
        JSON error response
    """
    request_id = str(uuid.uuid4())

    # Log error
    logger.error(
        f"Request ID: {request_id}, Error: {str(exc)}",
        exc_info=True,
    )

    # Try to log to database
    try:
        db = next(get_db())
        error_log = ErrorLog(
            request_id=request_id,
            error_type=type(exc).__name__,
            message=str(exc),
            endpoint=str(request.url.path),
            method=request.method,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(error_log)
        db.commit()
    except Exception as db_error:
        logger.error(f"Failed to log error to database: {str(db_error)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# Include routers
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(security.router)
app.include_router(dev_tools.router)
app.include_router(whitelabel.router)
app.include_router(learn.router)


# Mount static files for uploads
static_dir = Path("uploads")
if static_dir.exists():
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount self-hosted JS dependencies (React, Babel, etc.)
js_static_dir = Path("static")
if js_static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


# Health check endpoint
@app.get("/api/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# API info endpoint
@app.get("/api/info")
async def api_info() -> dict:
    """API info endpoint."""
    return {
        "name": "LMS Course Builder API",
        "version": "2.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


def _serve_frontend():
    """Helper to serve the frontend index.html."""
    frontend_index = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return JSONResponse(status_code=404, content={"detail": "Frontend not found"})


# Root serves the SPA
@app.get("/")
async def root():
    """Serve the SPA frontend."""
    return _serve_frontend()


# Catch-all for SPA (serve index.html for non-API routes)
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """
    Catch-all route for SPA.
    Serves index.html for non-API routes to enable client-side routing.
    """
    # Don't serve files for API routes
    if full_path.startswith("api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"},
        )

    return _serve_frontend()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
