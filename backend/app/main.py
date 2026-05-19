import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


@app.get("/")
def root():
    return {"message": "Distributed Cloud Storage API running"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(router)
