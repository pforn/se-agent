from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    openrouter_api_key: str = ""
    tavily_api_key: str = ""
    data_dir: Path = Path("./data")

    @property
    def checkpoints_dir(self) -> Path:
        return self.data_dir / "checkpoints"

    @property
    def chromadb_dir(self) -> Path:
        return self.data_dir / "chromadb"

    @property
    def app_db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def langgraph_db_path(self) -> Path:
        return self.checkpoints_dir / "langgraph.db"


settings = Settings()
