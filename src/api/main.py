"""
FastAPI application for Giswater Hydraulic Engine.
Provides endpoints for uploading and managing INP files for hydraulic modeling.
Following similar patterns to the giswater-api for consistency.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routes import router as inp_router
from .database import create_db_and_tables

TITLE = "Giswater Hydraulic Engine API"
VERSION = "0.1.0"
DESCRIPTION = "API for managing INP files and hydraulic modeling with EPANET."


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    try:
        create_db_and_tables()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
    
    yield
    
    # Shutdown
    print("Application shutting down")


app = FastAPI(
    version=VERSION,
    title=TITLE,
    description=DESCRIPTION,
    root_path="/api",
    lifespan=lifespan
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Serve static files (uploaded files)
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# Include routers
app.include_router(inp_router)


@app.get("/")
async def root():
    """Root endpoint providing API information"""
    return {
        "status": "Accepted",
        "message": f"{TITLE} is running.",
        "version": VERSION,
        "description": DESCRIPTION
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "Accepted",
        "message": "Service is healthy",
        "version": VERSION
    }


# Favicon endpoint
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve favicon if available"""
    favicon_path = os.path.join("static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return {"message": "No favicon available"}
