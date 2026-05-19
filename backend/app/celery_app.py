from celery import Celery

from app.config.settings import settings

broker_url = settings.redis_url or "redis://localhost:6379/0"

celery_app = Celery("distributed_storage", broker=broker_url, backend=broker_url)
