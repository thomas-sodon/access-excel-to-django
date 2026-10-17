# Staging: Northwind

This page tells you how to deploy the Northwind Django app to a staging server. The S5 client gate follows it. It is written from the engagement settings: hosting provider `none`, managed by us; sign-in `local`; primary database PostgreSQL, also verified on SQL Server. It also uses the settings the app reads from its environment (`app/config/settings/`).

The page holds names only. It has no values, passwords or secret values. Each secret is named by its reference in the engagement's `secrets` block (`env:NAME` or `pass:<path>`). The operator stores the value under that reference and nowhere else. Never put a value in this page, a repo, a ticket or a chat.

**Demo status.** This is the public Northwind demo. No staging server is set up, `secrets.staging_db_url_ref` is null and no secret reference is set. The steps below are what a client staging deployment runs. The demo runs them on a host of its own when one is chosen.

## The host

Hosting provider `none` means a generic Linux host that we manage. One server runs gunicorn behind a reverse proxy, such as nginx or Caddy, that ends TLS.

| Need | Detail |
|---|---|
| Operating system | A current 64-bit Linux, for example Ubuntu 24.04 LTS |
| Python | 3.13 through [uv](https://docs.astral.sh/uv/), the version the repo's CI uses (0.13.1). The app pins `requires-python = "==3.13.*"`. |
| System libraries | WeasyPrint needs Pango and HarfBuzz (`libpangoft2-1.0-0`, `libharfbuzz-subset0` on Ubuntu). SQL Server also needs `unixodbc`; the driver comes with `mssql-python`. |
| Database | An empty PostgreSQL 16 database, or a SQL Server 2022 database, with a login that owns it. The client's DBA creates it. The app never creates or drops it. |
| Reverse proxy | Ends HTTPS and forwards to gunicorn with `X-Forwarded-Proto` set. The app trusts that header (`SECURE_PROXY_SSL_HEADER`). |
| Service manager | systemd, or the host's equivalent, keeps gunicorn running and restarts it at boot. |

## Settings

The app runs with `DJANGO_SETTINGS_MODULE=config.settings.production`. That is the default in `config/wsgi.py`; set it explicitly for `manage.py` too. It reads these environment variables. Put them in the service's environment file, which only the service account can read. Do not put them in `app/.env`: production also reads that file when it exists, and it is meant for development.

| Variable | Needed | What it is | Filled from |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | yes | `config.settings.production` | plain setting |
| `DATABASE_URL` | yes | The staging database: `postgres://...` or `mssql://...` with the login. SQL Server URLs get the `mssql_python` driver automatically. | `secrets.staging_db_url_ref` (not set in the demo) |
| `DJANGO_SECRET_KEY` | yes | Django's signing key, at least 50 random characters, used for this deployment only | a secret the operator generates and stores under a reference of its own; the engagement has no slot for it yet (see below) |
| `DJANGO_ADMIN_URL` | yes | The admin's URL path, ending in `/`. Use a path that is hard to guess. | plain setting |
| `DJANGO_ALLOWED_HOSTS` | yes | The staging host name(s), comma-separated | plain setting |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | yes, behind HTTPS | `https://<staging host>`, comma-separated | plain setting |
| `DJANGO_SECURE_SSL_REDIRECT` | no (default on) | Redirect HTTP to HTTPS; `/health/` is exempt | plain setting |
| `DJANGO_SECURE_HSTS_SECONDS` | no (default 60) | HSTS age; keep it short on staging | plain setting |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | no (default on) | HSTS for subdomains | plain setting |
| `DJANGO_SECURE_HSTS_PRELOAD` | no (default on) | HSTS preload flag; turn it off on staging | plain setting |
| `DJANGO_SECURE_CONTENT_TYPE_NOSNIFF` | no (default on) | `X-Content-Type-Options: nosniff` | plain setting |
| `CONN_MAX_AGE` | no (default 60) | Seconds a database connection is kept | plain setting |
| `DJANGO_DEBUG` | no (default off) | Leave it off on staging | plain setting |
| `DJANGO_READ_DOT_ENV_FILE` | no | Off makes the app ignore `app/.env` even when it exists | plain setting |
| `DJANGO_ACCOUNT_ALLOW_REGISTRATION` | no (default off) | Leave it off: accounts come from the admin, `createsuperuser` or `create_demo_users` | plain setting |
| `DJANGO_ADMIN_FORCE_ALLAUTH` | no (default off) | Send the admin's sign-in through allauth | plain setting |
| `DJANGO_DBBACKUP_DIR` | no | Folder for `manage.py dbbackup` files, outside the repo | plain setting |
| `DJANGO_EMAIL_BACKEND` | no (default SMTP) | Django e-mail backend | plain setting |
| `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_USE_TLS` | for e-mail | SMTP server (defaults: localhost, 587, TLS on) | plain settings |
| `DJANGO_EMAIL_HOST_USER` | for e-mail | SMTP login | plain setting |
| `DJANGO_EMAIL_HOST_PASSWORD` | for e-mail | SMTP password | a secret under its own reference; the engagement has no slot for it (e-mail is not used in the demo) |
| `DJANGO_DEFAULT_FROM_EMAIL`, `DJANGO_SERVER_EMAIL`, `DJANGO_EMAIL_SUBJECT_PREFIX` | no | Sender addresses and subject prefix | plain settings |
| `DJANGO_MICROSOFT_CLIENT_ID`, `DJANGO_MICROSOFT_TENANT_ID` | no | Microsoft sign-in; leave unset, because sign-in is `local` | plain settings |
| `DJANGO_MICROSOFT_CLIENT_SECRET` | no | Microsoft sign-in secret; unset with local sign-in | `secrets.entra.client_secret_ref` (null) |
| `DJANGO_ENTRA_GROUP_ROLES` | no | JSON map from Entra group id to role; unset with local sign-in | plain setting |
| `DEMO_PASSWORD` | only for `create_demo_users` | The demo users' password, read once by that command | a secret under its own reference; set it only for that one command, never in the service's environment |

Never set these on staging: `PG_URL` (a development fallback when `DATABASE_URL` is missing), `MP_ONLY_AREAS` (it uninstalls feature areas), `MP_DB_SUFFIX` and `MP_TEST_DB_PREFIX` (they name test databases only).

## Deploy

Run every step as the service account, from `<checkout>/northwind/app`, with the settings above in the environment.

1. **Get the code.** Check out the release tag or branch the gate names. Then install the locked dependencies without the development group:

   ```sh
   uv sync --locked --no-dev
   ```

2. **Check the settings.** This fails on a missing setting:

   ```sh
   uv run python manage.py check --deploy
   ```

3. **Migrate.** This creates the tables in the empty database. It also creates the role groups (`staff`, `approver`) after the migration, because `core` syncs them on every `migrate`:

   ```sh
   uv run python manage.py migrate --noinput
   ```

4. **Collect static files.** Production serves them through WhiteNoise from `app/staticfiles/`:

   ```sh
   uv run python manage.py collectstatic --noinput
   ```

5. **Create the superuser.** This is the operator's own administrator account. The command asks for the e-mail address and the password. Type them in; never put them in a script:

   ```sh
   uv run python manage.py createsuperuser
   ```

   Give staff accounts a role in the admin (Users, then Groups): `staff`, or `approver` for people who approve purchase orders.

   Link every account that submits or approves purchase orders to its employee. A purchase order records the signed-in employee as submitter and approver, and refuses a user without one (rules R-purchasing-004 and R-purchasing-005). An account is linked to the employee whose e-mail address equals the account's sign-in e-mail, ignoring case. Without that link the account cannot submit or approve purchase orders. Set that address on the employee's record.

6. **Demo users (optional).** For a demo or the gate's click-through, create one user per role (`staff@example.com`, `approver@example.com`) and `admin@example.com`. The password is read from `DEMO_PASSWORD` for this one command:

   ```sh
   DEMO_PASSWORD="$(<read it from its secret reference>)" uv run python manage.py create_demo_users
   ```

   The command creates no employees. Before a demo user submits or approves a purchase order, give one employee that user's e-mail address, as step 5 describes. Do this after step 7, because a load with `--flush` replaces the employees.

7. **Load data.** In the demo, load synthetic seed 1. It is committed, so it is not client data:

   ```sh
   uv run python manage.py import_dataset ../goldens/synthetic/seed-1/input --flush
   ```

   For a client, the staging load of the engagement data is an operator step at the S5 client gate. It runs in a plain terminal and follows the runbook. It is never run from this page or by an agent.

8. **Start.** Start gunicorn under the service manager, bound to the local port the reverse proxy forwards to:

   ```sh
   uv run gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --access-logfile - --error-logfile -
   ```

   A systemd unit runs that line as `ExecStart` with `WorkingDirectory=<checkout>/northwind/app` and `EnvironmentFile=<the service's environment file>`. Set `Restart=on-failure`.

9. **Start-up job.** The orders area's `first_run` job (rule R-orders-049, listed in `northwind/orders/jobs.py`) runs once after each start of the application. Run it after step 8, and from the unit's `ExecStartPost` or a cron `@reboot` entry afterwards. The first-run flag makes every run after the first do nothing:

   ```sh
   uv run python manage.py first_run
   ```

10. **Check.** `https://<staging host>/health/` must answer 200. Sign in as a demo user. You should see the order list, then each area in the main menu: Orders, Invoicing and Shipping; Products and Inventory; Purchasing and receiving; Sales and Catalog Reports. Open an invoice as a PDF to prove WeasyPrint's libraries.

## Update a running staging server

Check out the new release. Then repeat steps 1 to 4, restart the service and repeat step 10. Back up the database first with `uv run python manage.py dbbackup`, which writes to `DJANGO_DBBACKUP_DIR`.

## Before the gate

These steps need a person:

- Choose the staging host and its name, and set up the reverse proxy with a certificate.
- Have the DBA create the empty staging database and its owner login. Store the database URL under `secrets.staging_db_url_ref` (runbook 1.6).
- Generate `DJANGO_SECRET_KEY` and store it under a secret reference. The engagement's `secrets` block has no slot for it, so record the reference in the gate notes.
- Fill the service's environment file from those references on the host. Only the service account may read it.
