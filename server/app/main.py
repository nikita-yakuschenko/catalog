from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import builds, catalogs, health, projects, proposals, sync
from app.core.config import settings
from pathlib import Path


def create_app() -> FastAPI:
    app = FastAPI(title="AVGST Catalog Builder", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    storage = Path(settings.storage_dir)
    output = Path(settings.output_dir)
    storage.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    app.mount("/storage", StaticFiles(directory=str(storage)), name="storage")
    app.mount("/output", StaticFiles(directory=str(output)), name="output")

    app.include_router(health.router, tags=["health"])
    app.include_router(sync.router, prefix="/api", tags=["sync"])
    app.include_router(projects.router, prefix="/api", tags=["projects"])
    app.include_router(catalogs.router, prefix="/api", tags=["catalogs"])
    app.include_router(builds.router, prefix="/api", tags=["builds"])
    app.include_router(proposals.router, prefix="/api", tags=["proposals"])
    return app


app = create_app()
