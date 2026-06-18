"""
Gunicorn configuration for DoxaEd OMR production deployment.

Usage:
    gunicorn config.wsgi:application -c gunicorn.conf.py

Override via environment variables:
    WEB_CONCURRENCY   — number of worker processes (default: cpu_count * 2 + 1)
    GUNICORN_TIMEOUT  — worker timeout in seconds (default: 120)
"""
import multiprocessing
import os

# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------
bind = "0.0.0.0:8000"

# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------
# Heroku / Railway / Render set WEB_CONCURRENCY; otherwise cpu * 2 + 1 is
# the classic gunicorn rule of thumb for sync workers.
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
# 120 s is generous enough for slow DB queries and multipart uploads.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
graceful_timeout = 30
keepalive = 5

# ---------------------------------------------------------------------------
# Logging — write to stdout/stderr so the process supervisor (Render,
# Heroku, systemd) captures logs centrally.
# ---------------------------------------------------------------------------
accesslog = "-"   # stdout
errorlog = "-"    # stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# ---------------------------------------------------------------------------
# Security / process title
# ---------------------------------------------------------------------------
proc_name = "omrflow"
# Limit request line + header size to guard against oversized requests.
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190
