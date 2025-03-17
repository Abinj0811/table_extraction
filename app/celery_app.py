# celery_app.py
from celery import Celery

# Initialize the Celery app with the Redis broker and backend
celery_app = Celery('app',
                    broker='redis://localhost:6379/0',
                    backend='redis://localhost:6379/0')

# Use autodiscovery to find tasks in specified modules
celery_app.autodiscover_tasks(['app.tasks'])

# Optional: Configure task routing if needed
celery_app.conf.update(task_routes={'tasks.process_pdf': {'queue': 'default'}})
