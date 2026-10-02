import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.routes.api import router as api_router
from backend.app.database.session import engine, Base

# Setup logger
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dukaanmitra.main")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("==================================================")
    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Tagline: {settings.APP_TAGLINE}")
    logger.info("Initializing database metadata...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to database on startup ({e}). Run setup_database.py once credentials are confirmed.")
    logger.info("==================================================")
    yield
    logger.info("Shutting down DukaanMitra...")

app = FastAPI(
    title=settings.APP_NAME,
    description="DukaanMitra — AI-powered Hinglish order desk for Indian shopkeepers. 'Aap Bolo, DukaanMitra Sambhale.'",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")
app.include_router(api_router)  # Also mount directly for root convenience


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please check server logs for details.",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "app": settings.APP_NAME,
        "tagline": settings.APP_TAGLINE,
        "docs": "/docs",
        "health": "/health",
        "status": "ready"
    }
