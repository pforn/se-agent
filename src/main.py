import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.db.app_db import init_db
from src.kb.store import get_kb_store
from src.ui.routes import router as ui_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.checkpoints_dir.mkdir(parents=True, exist_ok=True)
    settings.chromadb_dir.mkdir(parents=True, exist_ok=True)
    init_db(settings.app_db_path)
    logger.info("Warming up KB store and embedding model...")
    get_kb_store()
    logger.info("KB store ready")
    yield


app = FastAPI(title="Tower FDE Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/ui/static"), name="static")
app.include_router(ui_router)
