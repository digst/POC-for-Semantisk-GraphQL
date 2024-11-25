from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Database(BaseModel):
    user: str
    password: str
    host: str
    port: int = 5432
    name: str

    @property
    def url(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Allow e.g. `DATABASE__USER`
        env_nested_delimiter="__",
    )

    database: Database
