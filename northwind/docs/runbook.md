# Runbook: Northwind

This runbook is for the developer or administrator who runs the Northwind Django app: locally, on a server, through go-live and afterwards. It is written from the engagement settings: hosting provider `none` (a Linux host of your own), managed by us; sign-in `local`; primary database PostgreSQL 16, also verified on SQL Server 2022; and from the settings the app reads (`app/config/settings/`).

It holds names only: setting names and the names of secret references (`secrets.<field>` in the engagement, each `env:NAME` or `pass:<path>`), never a value. Values live only in the host's settings or secret store.

**Demo status.** This is the public Northwind demo. Nothing is deployed and no secret reference is set (`secrets` holds only nulls, `database.stage1` is null, `care_plan` is null): the public repository is the deliverable. The steps below are what a client deployment runs; the demo runs them on a host of its own when one is chosen. [staging.md](staging.md) is the staging version of the same steps.

## Run it locally

You need [uv](https://docs.astral.sh/uv/) (it installs Python 3.13 from `app/.python-version`), a PostgreSQL 16 server (or SQL Server 2022) you can create databases on, and these system libraries:

| For | Ubuntu or Debian packages |
|---|---|
| PDF invoices and reports (WeasyPrint) | `libpangoft2-1.0-0`, `libharfbuzz-subset0` |
| SQL Server (mssql-django imports pyodbc; the ODBC driver comes inside mssql-python) | `libodbc2`, `libltdl7` |
| `manage.py dbbackup` on PostgreSQL | `postgresql-client-16` (pg_dump) |

From `northwind/app/`:

```sh
uv sync                                                   # Python 3.13 and the locked packages, dev tools included
export DATABASE_URL=postgres://<user>:<password>@127.0.0.1:5432/northwind_demo
uv run python manage.py migrate                           # tables, plus the role groups staff and approver
uv run python manage.py import_dataset ../goldens/synthetic/seed-1/input --flush   # synthetic seed 1
DEMO_PASSWORD='<choose one>' uv run python manage.py create_demo_users            # staff@, approver@, admin@example.com
uv run python manage.py runserver
```

- `DATABASE_URL` may also be `mssql://<user>:<password>@127.0.0.1:1433/northwind_demo`; the app adds the `mssql_python` driver option, and `TrustServerCertificate=yes` for a local server. Without `DATABASE_URL` the app uses `$PG_URL/northwind_demo`, and `app/.env` (gitignored) may hold `DATABASE_URL` for development.
- Open http://127.0.0.1:8000/ and sign in as `staff@example.com` with the password you chose. You land on the order list.
- A demo user can submit or approve purchase orders only when an employee record has the same e-mail address (see Users and roles).

Tests, from `northwind/app/`:

```sh
uv run playwright install chromium        # once, for the end-to-end tests
uv run pytest -q --create-db              # the whole suite on DATABASE_URL, end-to-end tests included
DATABASE_URL=mssql://... uv run pytest -q --create-db --ignore=tests/e2e   # SQL Server
uv run ruff check . && uv run ruff format --check .
```

The test database is `test_northwind_demo` (with `MP_DB_SUFFIX` set, `test_northwind_demo_<suffix>`). The repository's CI (`.github/workflows/northwind.yml`) runs the same suite on PostgreSQL and SQL Server service containers, the end-to-end tests, and the equivalence harness on the synthetic seeds.

## Configuration and secrets

Production runs with `DJANGO_SETTINGS_MODULE=config.settings.production` (the default in `config/wsgi.py`; set it for `manage.py` too, which defaults to `config.settings.local`). The app reads these settings from its environment, by name:

| Setting | Needed in production | What it is | Filled from |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | yes | `config.settings.production` | plain setting |
| `DATABASE_URL` | yes | The production database, `postgres://...` or `mssql://...` with its login | `secrets.production_db_url_ref` (not set in the demo) |
| `DJANGO_SECRET_KEY` | yes | Django's signing key, at least 50 random characters, for this deployment only | a secret under a reference of its own; the engagement's `secrets` block has no slot for it |
| `DJANGO_ADMIN_URL` | yes | The admin's URL path, ending in `/`; hard to guess | plain setting |
| `DJANGO_ALLOWED_HOSTS` | yes | Host names, comma-separated | plain setting |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | yes, behind HTTPS | `https://<host>`, comma-separated | plain setting |
| `DJANGO_SECURE_SSL_REDIRECT` | no (default on) | Redirect HTTP to HTTPS; `/health/` is exempt | plain setting |
| `DJANGO_SECURE_HSTS_SECONDS` | no (default 60) | HSTS age; raise it (for example to 31536000) once HTTPS works | plain setting |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | no (default on) | HSTS for subdomains | plain setting |
| `DJANGO_SECURE_HSTS_PRELOAD` | no (default on) | HSTS preload flag | plain setting |
| `DJANGO_SECURE_CONTENT_TYPE_NOSNIFF` | no (default on) | `X-Content-Type-Options: nosniff` | plain setting |
| `CONN_MAX_AGE` | no (default 60) | Seconds a database connection is kept | plain setting |
| `DJANGO_DEBUG` | no (default off) | Never on in production | plain setting |
| `DJANGO_READ_DOT_ENV_FILE` | no | Off makes the app ignore `app/.env` even when the file exists | plain setting |
| `DJANGO_ACCOUNT_ALLOW_REGISTRATION` | no (default off) | Self-registration; leave it off | plain setting |
| `DJANGO_ADMIN_FORCE_ALLAUTH` | no (default off) | Send the admin's sign-in through allauth (and its MFA) | plain setting |
| `DJANGO_DBBACKUP_DIR` | no (default `app/backups/`) | Folder for `manage.py dbbackup` files, outside the checkout | plain setting |
| `DJANGO_EMAIL_BACKEND` | no (default SMTP) | Django e-mail backend | plain setting |
| `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_USE_TLS` | for e-mail | SMTP server (defaults localhost, 587, TLS on) | plain settings |
| `DJANGO_EMAIL_HOST_USER` | for e-mail | SMTP login | plain setting |
| `DJANGO_EMAIL_HOST_PASSWORD` | for e-mail | SMTP password | a secret under a reference of its own; no slot in the engagement (e-mail is not used in the demo) |
| `DJANGO_DEFAULT_FROM_EMAIL`, `DJANGO_SERVER_EMAIL`, `DJANGO_EMAIL_SUBJECT_PREFIX` | no | Sender addresses and subject prefix | plain settings |
| `DJANGO_MICROSOFT_CLIENT_ID`, `DJANGO_MICROSOFT_TENANT_ID` | only with Microsoft sign-in | Turns Microsoft sign-in on (see Microsoft sign-in) | plain settings |
| `DJANGO_MICROSOFT_CLIENT_SECRET` | only with Microsoft sign-in | The app registration's client secret | `secrets.entra.client_secret_ref` (null: sign-in is `local`) |
| `DJANGO_ENTRA_GROUP_ROLES` | only with Microsoft sign-in | JSON object from Entra group object id to role name | plain setting, built from `auth.groups_to_roles` |
| `DEMO_PASSWORD` | never in the service | The demo users' password, read once by `create_demo_users` | set only for that one command |

Development and test variables, never set in production: `PG_URL` and `MSSQL_URL` (server URLs for development and the harness), `MP_ONLY_AREAS` (installs only the named feature areas), `MP_DB_SUFFIX` and `MP_TEST_DB_PREFIX` (test database names), `E2E_SCREENSHOT_DIR` and `E2E_VIDEO_DIR` (end-to-end screenshots and video), and the harness's `EQUIVALENCE_*` variables.

Put the production settings in the service's environment file (readable by the service account only) or the host's secret store. Do not put them in `app/.env`: production reads that file too when it exists, and it is meant for development. Nobody pastes a value into a file in the repository, a ticket, a prompt or a chat.

## Deploy

Hosting provider `none`: one Linux server runs gunicorn behind a reverse proxy that ends TLS, with PostgreSQL 16 or SQL Server 2022 as the database. [deploy/README.md](deploy/README.md) is the production checklist with a systemd unit; in short, from `northwind/app/` as the service account with the settings above:

1. `uv sync --locked --no-dev`
2. `uv run python manage.py check --deploy`
3. `uv run python manage.py migrate --noinput` (also syncs the role groups)
4. `uv run python manage.py collectstatic --noinput` (WhiteNoise serves `app/staticfiles/`)
5. Start `uv run --no-sync gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3` under systemd, behind the reverse proxy.
6. Install the scheduled jobs below.
7. `https://<host>/health/` answers 200 (`{"status": "ok"}` once the database answers).
8. `uv run python manage.py createsuperuser` for the first administrator (type the password; never script it).

If the app later moves to Azure App Service instead, the same steps map onto Microsoft Learn's "Deploy a Python (Django, Flask, or FastAPI) web app to Azure App Service" and "Configure a Python app for Azure App Service" (the pipeline has a deploy template for that provider), and scheduled jobs become WebJobs ("Run background tasks with WebJobs in Azure App Service").

Who runs it: `hosting.managed_by` is `us`, which for a client needs a purchased care plan; without one the hosting is handed to the client or their MSP at acceptance (see [access-and-ownership.md](access-and-ownership.md)).

### Scheduled jobs

| Command | Schedule | Rule | What it does |
|---|---|---|---|
| `first_run` | `@reboot` | R-orders-049 | The original's start-up routine: on the very first run only (guarded by the first-run flag in the system settings) it moves every date forward so sample data looks current, then sets the flag. Every later run prints that it is already done and changes nothing. |

The jobs are listed in `app/northwind/orders/jobs.py`; each is a management command, run as `uv run --no-sync python manage.py <command>` from `northwind/app/` with the service's environment. With hosting provider `none`, run `first_run` once after each start of the app with a systemd timer (it is the `@reboot` schedule; a cron `@reboot` line works too):

```ini
# /etc/systemd/system/northwind-first-run.service
[Unit]
Description=Northwind start-up job first_run (R-orders-049)
After=northwind.service
Requires=northwind.service

[Service]
Type=oneshot
User=northwind
WorkingDirectory=/srv/northwind/northwind/app
EnvironmentFile=/etc/northwind/env
ExecStart=/usr/local/bin/uv run --no-sync python manage.py first_run
```

```ini
# /etc/systemd/system/northwind-first-run.timer
[Unit]
Description=Run the Northwind start-up job after boot

[Timer]
OnBootSec=2min
Unit=northwind-first-run.service

[Install]
WantedBy=timers.target
```

Enable it with `systemctl enable --now northwind-first-run.timer`. Paths, user and environment file are examples; use the ones of your host. On a production database loaded from real data, check the first-run flag in the system settings before the first start: if it is not set, `first_run` would shift every date once. Decide with the client whether to set the flag or leave the timer out (the answer to Q-orders-005 keeps the job as a one-off command guarded by that flag).

## Go-live and smoke checklist

The original is an Access application, so go-live moves its data once, from a fresh copy, into the production database. The engagement facts for it (`database.stage1`: `freeze_window`, `fresh_copy`, `rollback`) are not set (demo): there is no client cutover. For a client it runs like this, with the operator in a plain terminal on the operator host:

1. **Freeze.** In the agreed freeze window (`database.stage1.freeze_window`, not set (demo)) users stop changing data in Access, and the client saves a fresh copy of the database at the agreed place (`database.stage1.fresh_copy`, not set (demo)).
2. **Load** the fresh copy into the production database named by `secrets.production_db_url_ref`:
   ```sh
   mp-data stage1 /home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/engagement.json --target-db secret:production_db_url_ref --dataset fresh-copy
   ```
3. **Verify** the load (counts only, every table must have rows) and keep the report:
   ```sh
   mp-data stage1 /home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/engagement.json --target-db secret:production_db_url_ref --dataset fresh-copy --verify --require-rows --report /home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/golive-report.md
   ```
4. **Migrate** the app onto the loaded tables, with `DATABASE_URL` set from `secrets.production_db_url_ref` in the service's environment, from `northwind/app/`:
   ```sh
   uv run python manage.py migrate --fake-initial
   uv run python manage.py migrate
   ```
   When Stage 1 was sold and its database is the production database, the data is already there: skip steps 2 and 3 and run only these two migrate lines. (Stage 1 was not sold for the demo; [stage1-runbook.md](stage1-runbook.md) describes the Access-over-ODBC rehearsal and how Access is relinked.)
5. **Start** the app, create the first administrator and the users (Users and roles), and run the smoke checklist below with a client user.
6. **Parallel period** (`database.stage1.rollback`, not set (demo)): Access stays available read-only, or relinked to the production database as [stage1-runbook.md](stage1-runbook.md) describes, until the agreed end date. If the rollback trigger agreed with the client happens before then, users go back to Access and the go-live is repeated later from a new fresh copy.

Smoke checklist (one item per workflow of `analysis/rules.json` and per kept report; tick each with a client user):

- [ ] **order_to_ship** (order entry to invoice, printable PDF, to shipping): sign in and land on the order list; start a new order, choose the customer, save; add a line that is Allocated; create the invoice and download its PDF; ship it (shipped date, shipper); receive payment; close it. The status badge moves New, Invoiced, Shipped, Paid, Closed.
- [ ] **inventory_restock** (inventory levels and restocking): on a product, enter a stock take; the product list shows its stock figures; for a product below its target level, use Reorder, pick a vendor, and see it on the vendor's New purchase order.
- [ ] **purchase_order_to_stock** (purchase order to receiving to stock update): create a purchase order for a vendor, add lines, submit, approve (as an approver linked to an employee), receive; the product's available stock rises; close it with the shipping fee and payment method.
- [ ] **kept_reports** (the invoice and the four chosen reports): open Reports from the main menu; each report below previews and saves as PDF.
- [ ] Invoice (`rptInvoice`): opens from an invoiced order and as a PDF (`Invoice PDF`), with the order number and total.
- [ ] Monthly sales per employee (`rptSalesByEmployee`): previews for the default period, filters to one salesperson, saves as PDF.
- [ ] Monthly sales per product (`rptSalesByProduct`): previews with its chart, saves as PDF.
- [ ] Quarterly sales per product (`rptSalesByProductQuarterly`): previews, quarters sorted by year then quarter, saves as PDF.
- [ ] Product catalog (`rptProductCatalog`, with its table of contents, fixed pages, order form and shipper list): generates with the date inputs hidden and saves as PDF.
- [ ] `/health/` answers 200 and the admin opens at `DJANGO_ADMIN_URL` for the administrator only.

## Backups and restore drill

- **Managed backups.** With hosting provider `none`, the database's own backups are the primary copy: for PostgreSQL, scheduled `pg_dump` or a base backup with WAL archiving (point-in-time recovery) run by the client's DBA or the managed database service; for SQL Server or Azure SQL, its automated full and log backups. Keep at least 14 days, and store one copy off the host.
- **Portable copy with django-dbbackup.** From `northwind/app/`, with the production settings:
  ```sh
  uv run python manage.py dbbackup --compress               # writes to DJANGO_DBBACKUP_DIR
  uv run python manage.py listbackups
  uv run python manage.py dbrestore --uncompress -i <file>  # into the database in DATABASE_URL
  ```
  On PostgreSQL it runs `pg_dump`/`pg_restore` (install `postgresql-client-16` on the host). On SQL Server, django-dbbackup has no native connector and falls back to Django's `dumpdata`/`loaddata` JSON, which is fine for a portable copy but slower; use the server's own backups as the primary copy there.
- **Restore drill.** Once at go-live and then at the interval the care plan sets (for example quarterly): restore the latest backup into a scratch database (never the production one), point a staging copy of the app at it (`DATABASE_URL`), run the smoke checklist above, then drop the scratch database. Record the date and the result in the engagement's records (`log.md`) and tell the client.

## Users and roles

Roles mirror the original's privileges (`app/northwind/core/local/roles.py`); each is a Django group, created and updated on every `migrate`:

| Role | Label | May do | Rules |
|---|---|---|---|
| `staff` | Staff | Everything a signed-in employee may do in the original: orders, invoices, shipping, products, stock takes, purchase orders up to submitting, reports. Nobody adds or deletes rows of the fixed code lists or changes a saved stock take. | R-orders-050, R-orders-047, R-purchasing-003, R-orders-001, R-inventory-011 |
| `approver` | Purchase order approver | Staff plus approving purchase orders (the original's approve-purchase-order privilege) | R-purchasing-005, R-orders-050, R-inventory-011 |

- **Add a user:** in the admin (`DJANGO_ADMIN_URL`), Users, Add: e-mail address and a first password, tick Staff status, then add the group `staff` or `approver`. Registration is closed (`DJANGO_ACCOUNT_ALLOW_REGISTRATION` off). Mark the user's e-mail address as verified (Email addresses in the admin), because sign-in requires a verified address.
- **Link to an employee:** a user is the employee whose e-mail address equals the user's sign-in e-mail, ignoring case. Purchase orders record the signed-in employee as submitter and approver and refuse a user without one (R-purchasing-004, R-purchasing-005). Set that e-mail on the employee's record.
- **MFA:** django-allauth's MFA is installed. Each user can add an authenticator app and recovery codes under their account (`/accounts/2fa/`). Ask every administrator to turn it on, and set `DJANGO_ADMIN_FORCE_ALLAUTH` so the admin's sign-in goes through it.
- **Leavers:** untick Active on the user (keeps the audit history) rather than deleting it.
- **Demo users:** `create_demo_users` makes `staff@example.com`, `approver@example.com` and the superuser `admin@example.com` with the password in `DEMO_PASSWORD`. It is for demos and tests only; never run it on a production database.

## Microsoft sign-in

The engagement's sign-in is `local`: users sign in with e-mail and password, and Microsoft sign-in is off (`DJANGO_MICROSOFT_CLIENT_ID` is unset). To turn it on later:

1. The client's Entra administrator registers an application in the client's tenant (Microsoft Learn: "Quickstart: Register an application with the Microsoft identity platform"), web platform, with the redirect URI `https://<host>/accounts/microsoft/login/callback/`.
2. They add a client secret (Microsoft Learn: "Add and manage application credentials in Microsoft Entra ID") and store it under a secret reference named in the engagement as `secrets.entra.client_secret_ref` (now null), with its expiry date in `secrets.entra.secret_expires`. The value goes only into the host's secret store as `DJANGO_MICROSOFT_CLIENT_SECRET`.
3. Set `DJANGO_MICROSOFT_CLIENT_ID` (the application id) and `DJANGO_MICROSOFT_TENANT_ID` (the tenant id; default `organizations`). The app then offers Microsoft sign-in through django-allauth's Microsoft provider, with the scopes openid, email, profile and User.Read.
4. For roles from Entra groups, enable the groups claim in the registration's token configuration and set `DJANGO_ENTRA_GROUP_ROLES` to a JSON object from group object id to role (`staff` or `approver`), built from the engagement's `auth.groups_to_roles`.
5. **Secret expiry:** a client secret expires (at most 24 months). Put the date in the care plan calendar; before it, add a new secret, update the host setting, restart, and delete the old secret.

## Updates and Django LTS

- **Django 5.2 LTS** receives security releases until April 2028. Apply each one promptly: raise the `django==5.2.x` pin in `app/pyproject.toml`, `uv lock`, run the whole suite on PostgreSQL and SQL Server and the equivalence harness on the seeds, then deploy as in Deploy.
- **Django 6.2 LTS** is planned for April 2027. Plan the move after it is out (and after cookiecutter-django and the packages above support it), well before 5.2's end of support: first run the suite with deprecation warnings as errors (`uv run pytest -q --create-db -W error::DeprecationWarning`) and fix what it finds on 5.2, then read the release notes, upgrade, and run every check.
- **Other packages:** `uv lock --upgrade-package <name>`, read its changelog, run the suites. `pyproject.toml` `[tool.uv] exclude-newer` keeps the lock reproducible; move that date forward when you upgrade on purpose.
- **Python 3.13** is supported upstream until October 2029. **WeasyPrint** and the **ODBC driver** come from PyPI with the packages; the host's system libraries come from its OS updates.
- Who does it: the care plan when one is purchased (none for the demo); otherwise the client's developer.

## Equivalence checks

The vendored harness in `../equivalence/` re-runs every kept query of the original against the app and compares the result with the recorded golden, without our toolkit. The goldens were recorded by UCanAccess 5.1.8 running the original's queries, not by Microsoft Access; the 7 kept units flagged `needs_access_confirmation` in `goldens/manifest.json` were not confirmed on Access, so for them a pass shows agreement with UCanAccess only (report, Known differences). A client who has Access can confirm them on a Windows + Access machine. On the synthetic seeds it runs anywhere ([equivalence/README.md](../equivalence/README.md)). From `northwind/app/`, one cell:

```sh
PG_URL=postgresql://<user>:<password>@127.0.0.1:5432 \
uv run python -m pytest -c pyproject.toml --rootdir . ../equivalence/tests -p equivalence.plugin \
  --create-db --eq-adapter ../equivalence/adapter.toml --eq-dataset seed-1 --eq-db postgresql \
  --junitxml junit-equivalence-seed-1-postgresql.xml -p no:cacheprovider
```

Repeat for `seed-2` and `seed-3`, and with `--eq-db mssql` (`MSSQL_URL`). CI runs these on every pull request. Re-run them after any change to a kept query, report or stock calculation. The engagement dataset (the original's own data) runs only on our side through the data plane, with redacted output.

Current figures (`equivalence/results.json`, 2026-10-17): lowest cell rate 1.0 and pooled rate 1.0 over 8 cells (engagement and seeds 1 to 3, on PostgreSQL and SQL Server; threshold 0.9); rule tests 157 of 157 on each database; end-to-end tests 5 of 5 on PostgreSQL. The full report is [equivalence-report.md](equivalence-report.md).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ImproperlyConfigured: No database configured` | Neither `DATABASE_URL` nor `PG_URL` is set | Set `DATABASE_URL` in the service's environment |
| `OSError: cannot load library 'libpangoft2-1.0...'` or `libgobject` when a PDF is made | WeasyPrint's system libraries are missing | Install `libpangoft2-1.0-0` and `libharfbuzz-subset0` |
| `libodbc.so.2` or `libltdl.so.7: cannot open shared object file` on SQL Server | The ODBC manager libraries are missing | Install `libodbc2` and `libltdl7` |
| SQL Server: certificate verify failed | A remote server without a trusted certificate | Give the server a trusted certificate; only a local server gets `TrustServerCertificate=yes` |
| 400 Bad Request | Host not in `DJANGO_ALLOWED_HOSTS` | Add it |
| 403 CSRF verification failed behind the proxy | Origin not trusted, or the proxy does not set `X-Forwarded-Proto` | Set `DJANGO_CSRF_TRUSTED_ORIGINS=https://<host>`; forward the header |
| Redirect loop on HTTP | The proxy does not pass `X-Forwarded-Proto: https` | Fix the proxy, or end TLS before gunicorn |
| Static files 404 (no styling) | `collectstatic` not run after an update | Run it and restart |
| Sign-in returns to "Verify your e-mail address" | The user's e-mail address is not verified | Verify it in the admin (Email addresses) |
| A user cannot submit or approve purchase orders | No employee with the user's e-mail, or not in `approver` | Set the employee's e-mail; add the group |
| A role lacks permissions after an update | Groups are synced by `migrate` | Run `manage.py migrate` |
| `/health/` returns 500 | The database does not answer | Check `DATABASE_URL`, the network and the database server |
| `dbbackup` fails with `pg_dump: not found` | PostgreSQL client tools missing | Install `postgresql-client-16` |
| End-to-end tests fail with "Executable doesn't exist" | Playwright's browser is not installed | `uv run playwright install chromium` |
