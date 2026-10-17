# Deploy: Northwind on your own Linux host

The engagement's hosting provider is `none`: the app runs on one Linux server that you (or your MSP) choose, with gunicorn behind a reverse proxy that ends TLS, and one database server. `hosting.managed_by` is `us`, so we would run it under a care plan; without one, the client or their MSP runs it after acceptance. This page is the generic production checklist; [../runbook.md](../runbook.md) has the settings, go-live, backups, users and scheduled jobs.

**Demo status.** No host is set up for the public demo; nothing is deployed. There are no provider files for hosting provider `none`.

## The host

| Need | Detail |
|---|---|
| Operating system | A current 64-bit Linux, for example Ubuntu 24.04 LTS |
| Python | 3.13 through [uv](https://docs.astral.sh/uv/); the app pins `requires-python = "==3.13.*"` |
| System libraries | WeasyPrint: `libpangoft2-1.0-0`, `libharfbuzz-subset0`. SQL Server: `libodbc2`, `libltdl7` (the ODBC driver itself comes with the mssql-python package). PostgreSQL backups with `dbbackup`: `postgresql-client-16` |
| Database | An empty PostgreSQL 16 database, or SQL Server 2022 / Azure SQL, with a login that owns it, created by the client's DBA. The app never creates or drops it. |
| Reverse proxy | nginx or Caddy, ending HTTPS and forwarding to gunicorn on 127.0.0.1:8000 with `X-Forwarded-Proto` set (the app trusts that header) |
| Service manager | systemd keeps gunicorn running and runs the scheduled jobs |
| Service account | One unprivileged user that owns the checkout and reads the environment file |

## Production checklist

- [ ] The code is checked out at the release tag, for example under `/srv/northwind`.
- [ ] `uv sync --locked --no-dev` from `northwind/app/` as the service account.
- [ ] The environment file (for example `/etc/northwind/env`, mode 600, owned by the service account) holds every production setting of the runbook's Configuration and secrets section, entered by the client or MSP from the secret references; `DJANGO_SETTINGS_MODULE=config.settings.production`.
- [ ] `uv run python manage.py check --deploy` reports no issues.
- [ ] `uv run python manage.py migrate --noinput` (or, at go-live, the load and the two migrate lines of the runbook's Go-live section).
- [ ] `uv run python manage.py collectstatic --noinput`.
- [ ] The first administrator: `uv run python manage.py createsuperuser` (typed, never scripted); MFA turned on for them.
- [ ] gunicorn runs under systemd (unit below) and restarts on failure.
- [ ] The reverse proxy serves HTTPS with a valid certificate; `DJANGO_SECURE_HSTS_SECONDS` raised once HTTPS works.
- [ ] `https://<host>/health/` answers 200.
- [ ] The scheduled jobs are installed (runbook, Deploy, Scheduled jobs).
- [ ] Database backups are on, one restore drill is done and recorded (runbook, Backups and restore drill).
- [ ] Logs: gunicorn and Django write to the journal (`journalctl -u northwind`); keep them as the client's policy says.
- [ ] `DJANGO_DEBUG` is off, registration is closed, `DEMO_PASSWORD` is not in the environment and `create_demo_users` was never run.
- [ ] The smoke checklist (runbook, Go-live and smoke checklist) passes with a client user.

## systemd service

An example unit; the paths, user and environment file are examples:

```ini
# /etc/systemd/system/northwind.service
[Unit]
Description=Northwind (gunicorn)
After=network-online.target
Wants=network-online.target

[Service]
User=northwind
Group=northwind
WorkingDirectory=/srv/northwind/northwind/app
EnvironmentFile=/etc/northwind/env
ExecStart=/usr/local/bin/uv run --no-sync gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --access-logfile - --error-logfile -
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`systemctl enable --now northwind`, then check `systemctl status northwind` and `/health/`.

## Updating

1. Back up: `uv run python manage.py dbbackup --compress` (and check the database's own backup ran).
2. Check out the new release tag.
3. `uv sync --locked --no-dev`, `uv run python manage.py check --deploy`, `uv run python manage.py migrate --noinput`, `uv run python manage.py collectstatic --noinput`.
4. `systemctl restart northwind`, then check `/health/` and run the smoke checklist.
