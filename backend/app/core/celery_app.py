from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    include=["app.worker"]
)

# Removed task_routes so tasks flow to the default 'celery' queue
celery_app.conf.task_always_eager = False
