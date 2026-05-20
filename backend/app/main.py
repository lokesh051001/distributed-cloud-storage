import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.config.settings import settings
from app.db import Base, engine
from app.routes.file_routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("distributed-cloud-storage")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized and API startup complete.")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    return {
        "message": "Distributed Cloud File Storage API Running"
    }
frontend_dir = Path(__file__).resolve().parents[2] / "frontend"

if settings.force_https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)

allow_origins = list(settings.cors_allowed_origins) if settings.cors_allowed_origins else ["http://127.0.0.1:5500"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def frontend_home():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"detail": "Frontend not found."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(router)

if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
