"""
Celery application for OMRFlow.

In development (and tests), CELERY_TASK_ALWAYS_EAGER=True (the default) means
every .delay() / .apply_async() call runs synchronously inline — no broker
required.  In production, set CELERY_TASK_ALWAYS_EAGER=False and provide a
real CELERY_BROKER_URL (e.g. Redis).
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("omrflow")

# Read configuration from Django settings using the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in installed apps (looks for <app>/tasks.py).
app.autodiscover_tasks()
