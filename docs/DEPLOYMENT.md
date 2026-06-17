# OMRFlow — Production Deployment Guide

> Tested stack: Ubuntu 22.04 LTS, PostgreSQL 15, Redis 7, Python 3.12, Node 20.
> The guide uses a single-server setup with Nginx as a reverse proxy. Scale to
> multiple dynos/containers by adding more `web` and `worker` processes.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Python    | 3.12+   | `pyenv` recommended |
| Node.js   | 20 LTS  | For building the React frontend |
| PostgreSQL| 15+     | Create DB + user before deploy |
| Redis     | 7+      | Required for Celery async workers |
| Nginx     | 1.24+   | TLS termination + static/media serving |

---

## 1. Clone the repository

```bash
git clone https://github.com/your-org/omr.doxaed.com.git /srv/omrflow
cd /srv/omrflow
```

---

## 2. Backend — Python environment

```bash
cd /srv/omrflow/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Environment variables

```bash
cp backend/.env.prod.example backend/.env
# Edit backend/.env — fill every placeholder value:
#   DJANGO_SECRET_KEY, DATABASE_URL, RAZORPAY_*, EMAIL_*, FIELD_ENCRYPTION_KEY, etc.
nano backend/.env
```

Key points:
- `DEBUG=False` **must** be set.
- `FIELD_ENCRYPTION_KEY` must stay constant after first deploy (rotating it
  orphans all encrypted student name records).
- `CELERY_TASK_ALWAYS_EAGER=False` so tasks run asynchronously via Redis.

---

## 4. Database — migrate + seed

```bash
cd /srv/omrflow/backend
source .venv/bin/activate
python manage.py migrate --noinput
python manage.py seed_plans     # seeds Free / Pro / School billing plans
```

---

## 5. Static files

```bash
python manage.py collectstatic --noinput
# Static files land in backend/staticfiles/ — WhiteNoise serves them via
# gunicorn; Nginx serves /media/ separately (see Nginx config below).
```

---

## 6. Gunicorn (web process)

```bash
# One-shot test:
cd /srv/omrflow/backend
source .venv/bin/activate
gunicorn config.wsgi:application -c gunicorn.conf.py

# As a systemd service — create /etc/systemd/system/omrflow-web.service:
[Unit]
Description=OMRFlow Gunicorn web worker
After=network.target

[Service]
User=omrflow
Group=omrflow
WorkingDirectory=/srv/omrflow/backend
EnvironmentFile=/srv/omrflow/backend/.env
ExecStart=/srv/omrflow/backend/.venv/bin/gunicorn config.wsgi:application -c gunicorn.conf.py
Restart=on-failure
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now omrflow-web
```

---

## 7. Celery worker (async tasks)

```bash
# As a systemd service — /etc/systemd/system/omrflow-worker.service:
[Unit]
Description=OMRFlow Celery worker
After=network.target redis.service

[Service]
User=omrflow
Group=omrflow
WorkingDirectory=/srv/omrflow/backend
EnvironmentFile=/srv/omrflow/backend/.env
ExecStart=/srv/omrflow/backend/.venv/bin/celery -A config worker -l info --concurrency=2
Restart=on-failure
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now omrflow-worker
```

---

## 8. Nginx — TLS, reverse proxy, media & static

```nginx
# /etc/nginx/sites-available/omrflow
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    client_max_body_size 20M;   # allow image/OMR-sheet uploads

    # Serve Django API
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Serve Django admin
    location /admin/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    # Serve uploaded media files directly
    location /media/ {
        alias /srv/omrflow/backend/media/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Serve React frontend (production build)
    location / {
        root /srv/omrflow/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/omrflow /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# Obtain TLS cert:
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 9. Frontend build

```bash
cd /srv/omrflow/frontend
npm ci
VITE_API_BASE_URL=https://yourdomain.com npm run build
# Output lands in frontend/dist/ — served by Nginx (see location / above).
```

`VITE_API_BASE_URL` must point at the API's public origin (no trailing slash).

---

## 10. Razorpay webhook

In the Razorpay dashboard configure the webhook URL:

```
https://yourdomain.com/api/v1/billing/webhook/
```

Set the webhook secret and copy it into `RAZORPAY_WEBHOOK_SECRET` in `.env`.
OMRFlow verifies the `X-Razorpay-Signature` header on every incoming event.

---

## 11. Smoke-test checklist

- [ ] `curl https://yourdomain.com/api/v1/health/` returns `{"status":"ok"}`
- [ ] Register a user → verify email link arrives → log in → JWT returned
- [ ] Admin panel `https://yourdomain.com/admin/` loads and is password-protected
- [ ] Upload a test question image via PATCH `/api/v1/questions/{id}/` → image URL returned
- [ ] Celery worker is running (`sudo systemctl status omrflow-worker`)
- [ ] Razorpay webhook receives a test ping → 200 response in dashboard

---

## Procfile (Heroku / Railway / Render)

A `Procfile` at the repo root is provided for PaaS deployments:

```
web:     cd backend && gunicorn config.wsgi:application -c gunicorn.conf.py
worker:  cd backend && celery -A config worker -l info --concurrency=2
release: cd backend && python manage.py migrate --noinput && python manage.py seed_plans
```

PaaS platforms run the `release` process before each deploy, automatically
migrating the database and seeding billing plans.
