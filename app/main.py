"""Main FastAPI application for Notion Context Service."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn

from .config import settings
from .api.endpoints import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "service": settings.title,
        "version": settings.version,
        "description": settings.description,
        "docs": "/docs",
        "health": "/api/v1/health",
        "query": "/api/v1/query?q=your_query_here"
    }

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {settings.title} v{settings.version}")
    
    # Validate configuration
    if not settings.notion_api_key:
        logger.warning("Notion API key not configured - some endpoints may not work")
    
    if not settings.notion_database_id:
        logger.info("Notion database ID not configured - using search across all accessible pages")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info(f"Shutting down {settings.title}")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
