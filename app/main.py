import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import APP_TITLE, APP_DESCRIPTION, APP_VERSION, STORAGE_DIR, BASE_DIR
from app.database import engine, Base
from app.api.v1 import jobs, certificates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for flexible integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(certificates.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


# Static dashboard files
STATIC_DIR = BASE_DIR / "app" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.api_route("/", methods=["GET", "HEAD"], tags=["Dashboard"], include_in_schema=False)
    def serve_dashboard():
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/", tags=["Dashboard"])
    def root():
        return {"message": "Welcome to Bulk Certificate Generator API. Visit /docs for Swagger API documentation."}
