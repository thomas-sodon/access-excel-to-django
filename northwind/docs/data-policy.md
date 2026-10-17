# Data policy: Northwind

This page says how the original application's data was handled while the app was built, what is in this repository, and what the running app stores. The engagement's data policy: failure output on the original data is always redacted, sessions may run in the cloud (`execution: cloud-allowed`, because the data is public sample data), the design is scrubbed before anyone reads it (`scrub_design: true`), and data is never committed (`commit_data: false`).

The source is Microsoft's public Northwind 2.0 template with its sample data. We handled it exactly as we handle a client's data, as a rehearsal: the same zones, tools, redaction and database rules apply.

## How your data was handled

- **Two zones.** Everything taken from the source lives in one private directory on the operator's host, outside every repository, split in two zones. The *design zone* holds the scrubbed object model and inventory (names and structure, with values such as e-mail addresses replaced by tokens), the reference catalog and synthetic outputs; people and AI sessions may read it. The *data zone* holds the source file, the exported dataset, the reference database built from it, the goldens recorded on it, the results and logs of runs on it, and the scrub map; nobody opens it directly.
- **Tools only.** Only the pipeline's data-plane tool, `mp-data`, reads the data zone. Each call runs in a jail, writes its full output into the data zone, and prints one summary with names, counts and hashes, never values. Agent sessions run every other command in a sandbox where the data-zone folders look empty.
- **Redaction.** When a test on the original data fails, the terminal and the JUnit files show only the test, the number of differing rows and the column names; the detail stays in the private logs.
- **Databases.** Rows of the original data enter only local databases whose names start with `mpdata_` (here `mpdata_northwind_demo_stage1` and the `mpdata_test_northwind_demo_*` test databases), through `mp-data` only. The development login cannot open them; the app's development and test databases (`northwind_demo`, `northwind_demo_dev`, `test_northwind_demo_*`) hold synthetic data or the schema only.
- **Nothing in git.** No source file, export, sample output, data value, VBA, query or macro text is committed. Before every commit and push, a guard compares every file against a corpus built from the source, and a pre-commit hook rejects source and sample file types (.accdt, .accdb, .xlsm, .pdf, .xlsx and others).

## What is in this repository

- `analysis/`: the business rules and the keep/drop list, paraphrased from the scrubbed design; object, table and column names, no values.
- `app/`: the Django app, its tests and their hand-written fixtures.
- `goldens/`: three synthetic datasets (`seed-1` to `seed-3`, invented data generated from the data model) with their expected outputs, the parameter names the units take, and for the original data only HMAC-SHA256 digests of the recorded outputs, not the outputs.
- `equivalence/`: the harness and `results.json` (counts and unit names only).
- `docs/`: these documents, the equivalence report (counts and rates), screenshots of the app on synthetic seed 1, and wireframes reconstructed from the form definitions (no data).

## What the running app stores

| What | Where | Personal data |
|---|---|---|
| The business tables moved from the original (companies, contacts, employees, products, stock takes, orders, invoices, purchase orders and their lines, code lists, system settings) | the app's database (`legacy` models) | yes: names, e-mail addresses, phone numbers and addresses of contacts and employees |
| Users, their e-mail addresses, password hashes (argon2), groups | the app's database (`users`, allauth) | yes |
| MFA authenticators and recovery codes | the app's database (allauth MFA) | yes |
| Sessions | the app's database | yes (session keys) |
| Audit history of every change to the business tables, with the user who made it | the app's database (django-simple-history) | yes |
| Imports and exports through the admin (xlsx) | in memory; files go only where the user saves them | depends on the export |
| `dbbackup` files | `DJANGO_DBBACKUP_DIR` on the host | yes |
| Server logs (requests, errors) | the host's journal | IP addresses, user e-mail in error mails when `ADMINS` is set |

Invoices and reports are generated as PDF on request and not stored.

## Backups and access

- **Backups** are the database's own (managed) backups plus `dbbackup` copies, kept on the host and one copy off it, for the period agreed with the client (see the runbook's Backups and restore drill). They contain everything above.
- **Access.** The client owns the host, the database and the backups. Administrators of the app see every table in the admin; staff and approvers see what their role allows (runbook, Users and roles). We hold access only as [access-and-ownership.md](access-and-ownership.md) says, and what we hold of the original data is deleted as [data-retention.md](data-retention.md) says.
- **Demo.** Nothing is deployed for the demo, so no running app stores any of the above outside the operator's local test databases.
