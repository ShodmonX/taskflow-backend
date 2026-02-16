from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TaskFlow"
    env: str = "dev"
    debug: bool = True

    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 60

    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str

    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0

    rabbitmq_default_user: str = "admin"
    rabbitmq_default_pass: str = "admin"
    rabbitmq_host: str
    rabbitmq_port: int = 5672

    @property
    def database_url(self) -> str:
        # SQLAlchemy async URL
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        # Redis URL
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def rabbitmq_url(self) -> str:
        # RabbitMQ URL for Celery broker
        return f"amqp://{self.rabbitmq_default_user}:{self.rabbitmq_default_pass}@{self.rabbitmq_host}:{self.rabbitmq_port}//"


settings = Settings()  # type: ignore
