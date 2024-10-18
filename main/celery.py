from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitbit_app.settings')

app = Celery('fitbit_app')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.

redis_url = os.getenv("REDIS_URL", "redis://")

if redis_url.startswith("rediss://"):
    redis_url += "?ssl_cert_reqs=required"


app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(CELERY_BROKER_URL=redis_url,
                CELERY_RESULT_BACKEND=redis_url)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


# set the default Django settings module for the 'celery' program.
@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
