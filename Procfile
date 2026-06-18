web: cd backend && gunicorn config.wsgi:application -c gunicorn.conf.py
worker: cd backend && celery -A config worker -l info --concurrency=2
release: cd backend && python manage.py migrate --noinput && python manage.py seed_plans
