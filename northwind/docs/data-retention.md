# Data retention: Northwind

This page lists what we hold of the original application's data, where it is, until when, and how its deletion is recorded. The source is Microsoft's public Northwind 2.0 template and its sample data; we hold and delete it as if it were a client's data.

## What we hold

| Item | Holds source data | Why we keep it |
|---|---|---|
| The source file, the Access template `northwind.accdt` (12,895,205 bytes, sha256 pinned in the engagement) | yes | every stage rebuilds from it |
| The dataset export of its tables | yes | loads, equivalence runs |
| The reference database built from the dataset | yes | records the goldens |
| The goldens recorded on the original data and their parameter values | yes | the equivalence checks |
| Results and logs of data-plane runs (JUnit, matrices, redacted logs) | yes (logs may hold failure detail) | the equivalence report |
| The scrub map (tokens to original values) | yes | scrubbing the design |
| The guard's corpus, built from the source | yes | the commit guard that checks no source text is committed |
| The design zone: scrubbed object model, inventory, reference catalog, synthetic outputs, reviewer scratch | no values (names and structure, tokens) | design work, reviews |
| Local databases on PostgreSQL and SQL Server: `mpdata_northwind_demo_stage1` and `mpdata_test_northwind_demo_*` | yes | Stage 1 rehearsal, data-plane test runs |
| Local databases `northwind_demo_dev`, `northwind_demo`, `test_northwind_demo_*` | no (schema only or synthetic data) | development and tests |
| Copies on a Windows + Access machine | none (no machine was used) | |
| The engagement records (`engagement.json`, `answers.md`, `log.md`, `runs/`) | no (names, counts, hashes) | the engagement's history |

On 2026-10-17 a purge dry run listed 13 top-level entries of the private directory (3,402 files, about 81 MB; the count grows as each run adds logs and results) and 5 local databases.

## Where it is

- The private directory `/home/cloudcli/engagements/northwind-demo/private` on the operator's host: the data zone (`sources/`, `datasets/`, `workbook/`, `reference/`, `goldens/`, `corpus/`, `results/`, `logs/`, `assets/`, `scrub-map.json`) and the design zone (`out/`, `review/`, `synthetic/`).
- The local Docker database servers on the same host: `mp-pg16` (PostgreSQL 16) and `mp-mssql22` (SQL Server 2022).
- Windows + Access machine copies (`environment.windows_box.copies`): none.
- Nowhere else: no cloud storage, no repository, no ticket or chat holds the data. The engagement records live in the pipeline repository at `/home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo` and hold no data values.

## When it is deleted

For a client, the end date is the acceptance date plus `data_policy.retention_days_after_acceptance` days, unless `care_plan.private_data` says to keep the data encrypted for the care plan. For this demo the retention period is not set (`retention_days_after_acceptance` is null): the data is public sample data, and every stage's prepare list can rebuild the private directory from the pinned source. It is kept until the operator decides to purge it; the S6 gate rehearses the purge with a dry run. The client (here: the operator) may ask for an earlier deletion at any time.

## How deletion is recorded

1. **Dry run.** In a plain terminal on the operator's host (mp-data reads the database superuser URLs from the operator's private settings):
   ```sh
   mp-data purge /home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/engagement.json --dry-run
   ```
   It lists what would be deleted: each top-level entry of the private directory with its file count and size, the engagement's databases on every running local server (`mpdata_northwind_demo_*`, `mpdata_test_northwind_demo_*`, `northwind_demo_dev`, `northwind_demo` and `test_northwind_demo_*`), the servers it could not check, and the Windows-box copies. It deletes nothing. Check the list against "What we hold" above.
2. **Purge.** On the end date, the same command without `--dry-run` deletes the private directory's contents and drops those databases. It writes the destruction record `/home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/destruction-record-<YYYY-MM-DD>.md` (a second purge on the same day writes `destruction-record-<YYYY-MM-DD>-<n>.md`, so no record is overwritten). If a database cannot be dropped, purge exits 1 and lists it under "Not dropped".
3. **The record** holds names, counts and hashes only, in the sections Deleted (path, files, bytes), Databases dropped (server, name), Servers not checked (server, reason), Sources (path and sha256 of the source file) and Copies to delete by hand (none for the demo).
4. **By hand.** We delete any Windows-box copies the record lists and note the date beside the record.
5. **Kept.** We commit the destruction record to the engagement records and send the client a copy.
