import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Distributed Cloud Storage API")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./distributed_storage.db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "temp")
    storage_dir: str = os.getenv("STORAGE_DIR", "storage")
    chunk_count: int = int(os.getenv("CHUNK_COUNT", "3"))
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    replication_factor: int = int(os.getenv("REPLICATION_FACTOR", "2"))
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    api_username: str = os.getenv("API_USERNAME", "admin")
    api_password: str = os.getenv("API_PASSWORD", "admin123")
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "dev-encryption-key")
    redis_url: str = os.getenv("REDIS_URL", "")
    enable_node_health_check: bool = os.getenv("ENABLE_NODE_HEALTH_CHECK", "true").lower() == "true"
    force_https_redirect: bool = os.getenv("FORCE_HTTPS_REDIRECT", "false").lower() == "true"
    node_names: tuple[str, ...] = tuple(
        node.strip()
        for node in os.getenv("NODE_NAMES", "node1,node2,node3").split(",")
        if node.strip()
    )
    cors_allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")
        if origin.strip()
    )
    allowed_extensions: tuple[str, ...] = tuple(
        ext.strip().lower()
        for ext in os.getenv("ALLOWED_EXTENSIONS", "*").split(",")
        if ext.strip()
    )


settings = Settings()
