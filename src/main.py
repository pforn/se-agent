from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.db.app_db import init_db
from src.ui.routes import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.checkpoints_dir.mkdir(parents=True, exist_ok=True)
    settings.chromadb_dir.mkdir(parents=True, exist_ok=True)
    init_db(settings.app_db_path)
    yield


app = FastAPI(title="Tower FDE Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/ui/static"), name="static")
app.include_router(ui_router)
