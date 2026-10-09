import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router


from app.database.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Ensure upload directories exist
    os.makedirs(f"{settings.UPLOAD_DIR}/resumes", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/documents", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/logos", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/admin/profile", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/posters", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/gallery", exist_ok=True)
    os.makedirs(f"{settings.UPLOAD_DIR}/press", exist_ok=True)


    # Initialize and seed database if necessary
    try:
        await init_db()
    except Exception as e:
        # Don't crash lifespan in testing if DB already verified
        pass

    yield



app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(
    api_router,
    prefix=settings.API_V1_STR,
)


from fastapi.staticfiles import StaticFiles

# Mount static files for uploaded resumes, documents, and logos
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Basic health check endpoint returning {status: ok}."""
    return {"status": "ok"}
