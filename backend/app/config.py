import os
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "DukaanMitra"
    APP_TAGLINE: str = "Aap Bolo, DukaanMitra Sambhale."
    APP_ENV: str = Field(default="development", validation_alias="APP_ENV")
    DEBUG: bool = Field(default=True, validation_alias="DEBUG")
    API_HOST: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    API_PORT: int = Field(default=8000, validation_alias="API_PORT")

    # PostgreSQL Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/dukaanmitra",
        validation_alias="DATABASE_URL"
    )
    POSTGRES_HOST: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    POSTGRES_DB: str = Field(default="dukaanmitra", validation_alias="POSTGRES_DB")
    POSTGRES_USER: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="postgres", validation_alias="POSTGRES_PASSWORD")

    # Semantic Search & Embeddings
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        validation_alias="EMBEDDING_MODEL"
    )
    EMBEDDING_DIM: int = Field(default=384, validation_alias="EMBEDDING_DIM")
    USE_PGVECTOR: bool = Field(default=True, validation_alias="USE_PGVECTOR")

    # Data Path
    DATA_DIR: str = Field(default="./data", validation_alias="DATA_DIR")

    @property
    def sync_database_url(self) -> str:
        """Returns fully URL-encoded connection string safe for passwords with @, $, %, etc."""
        if not self.DATABASE_URL or "<PASSWORD>" in self.DATABASE_URL:
            from urllib.parse import quote_plus
            enc_pwd = quote_plus(self.POSTGRES_PASSWORD)
            return f"postgresql+psycopg2://{self.POSTGRES_USER}:{enc_pwd}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self.DATABASE_URL

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }


settings = Settings()
