# Legal check: Northwind

This page checks that everything this repository publishes for the Northwind demo may be published: each path is our own work, derived from Microsoft's Northwind 2.0 names and structure only, third-party material under a licence that allows it and credited in [NOTICE.md](../NOTICE.md), or synthetic data. The repository `thomas-sodon/access-excel-to-django` is private until the S6 demo gate and public after it. The S6 handover wrote the first three sections and the Pre-flip checks table; the operator fills that table's Date, Commit and Result columns and the Decision at the gate.

## What is published

| Path | What it is | Class | Note |
|---|---|---|---|
| `northwind/README.md` | The app README: what it does, screens, how to run, test and verify it | own work | |
| `northwind/NOTICE.md` | Packages, bundled third-party files, THIRD_PARTY.md texts, template licence, source credit | own work | quotes third-party licence texts as their licences require |
| `northwind/.gitignore` | Ignore rules | own work | |
| `northwind/analysis/` | Business rules (`rules.json`, `rules.md`), keep/drop list, interfaces | derived from third-party names and structure | rules paraphrased from the scrubbed design; object, table and column names used as identifiers; no data, VBA, query or macro text |
| `northwind/app/` | The Django app, its tests and fixtures | own work | generated from cookiecutter-django (third-party licensed, BSD-3-Clause, credited in NOTICE.md); `legacy/` models carry the original's table and column names (derived from third-party names and structure); `core/vbacompat.py` follows Jackcess's documented behaviour, no Jackcess code (Apache-2.0, credited); Chart.js 4.5.1 vendored unchanged in `reports/static/reports/vendor/` (third-party licensed, MIT, credited); test fixtures hand-written or synthetic |
| `northwind/docs/` | Runbook, deploy checklist, data policy, access, retention, Stage 1 documents, health check, equivalence report, this page, the walkthrough script | own work | `img/after/` screenshots of the new app on synthetic seed 1 (own work, synthetic data); `img/before/` wireframes reconstructed from the form definitions (derived from third-party names and structure; no data, no screenshot of Access); `health-check.md` and the report hold counts and names only |
| `northwind/equivalence/` | The vendored equivalence harness and `results.json` | own work | `results.json` holds counts and unit names only |
| `northwind/goldens/` | Synthetic datasets `seed-1` to `seed-3` with their expected outputs; `manifest.json`; `params.json`; `reference/functions/` | synthetic data | the seeds are invented rows generated from the data model; the manifest holds unit names, statuses and HMAC-SHA256 digests of the outputs on the original data, not the outputs; `params.json` holds parameter names and seed values only; `reference/functions/` are our own rewrites of the original's stock functions as queries over its table and column names (derived from third-party names and structure) |
| `README.md` (root) | Repository README: shared header and one section per engagement | own work | the Northwind section embeds pictures from `northwind/docs/img/`; this engagement does not write the header or other engagements' sections |
| `NOTICE.md` (root) | Shared one-line header and one section per engagement | own work | the Northwind section credits the source, the trademarks and the Northwind app's third-party material; this engagement does not write the header or other engagements' sections |
| `LICENSE` (root) | MIT licence for our own code | own work | |
| `.gitignore`, `.gitattributes` (root) | Git settings | own work | |
| `.pre-commit-config.yaml` (root) | Hooks that forbid source and sample file types, ruff and djLint | own work | uses third-party hooks by reference (pre-commit-hooks, ruff, djLint), not copied |
| `.github/` (root) | CI workflows: the guard and the Northwind app CI | own work | uses third-party GitHub Actions by reference |

Not published: the source template (`northwind.accdt`), its data, exports, VBA, queries, macros and images, the goldens and results on the original data, the walkthrough video and every other file of the private directory. The guard and the pre-commit hooks check every commit for them.

## Derived from third-party material

The original is Microsoft's Northwind 2.0 Developer Edition, an Access database template (.accdt) published without a licence. From it we derived, and publish:

- **Names.** Table, column, query, form, report and code-list names, used as identifiers in the rules, the Django models (`legacy/`), the URL names (`form_<form>`, `report_<report>`), the equivalence units and the goldens' parameter names.
- **Structure.** The table layout and relations (as Django models and migrations), the workflows and screens (as Django views), and the before wireframes, which `toolkit wireframe` reconstructed from the form definitions' sections, control types, positions and captions, without data, row sources, expressions or code.
- **Behaviour, paraphrased.** Every business rule in `analysis/rules.md` is written in our own words from the scrubbed design. The app implements those statements in new code. `goldens/reference/functions/` restates four stock functions and two report-period functions as our own queries over the original's names.
- **Behaviour, checked.** The goldens on the original data were recorded on our side with UCanAccess 5.1.8 (Jackcess 5.1.7, HSQLDB 2.7.4) running the original's queries, not with Microsoft Access; only their digests are published. 7 of the 54 kept units are flagged `needs_access_confirmation` and were not confirmed on Microsoft Access (no Windows + Access run for this demo); the public README, app README and walkthrough say so and point to the report's Known differences.

Never copied or published: data values, VBA, query SQL, macro text, images, report layouts as files, the template file or any export of it. The tools that read the template (the pipeline's `mp-data` and toolkit) are not part of this repository.

## Licences

- **Our code:** MIT, in the root [LICENSE](../../LICENSE), for our own work only. `app/pyproject.toml` still carries `license = { text = "Not open source" }`, the default of the project generator's answers; for this public demo the root LICENSE governs, and the field is listed as a follow-up (it is outside this task's files).
- **The source:** Microsoft publishes Northwind 2.0 without a licence, so we use only its names and structure, as above, and never redistribute the file, its data or its VBA. Microsoft, Access and Northwind are Microsoft trademarks; the demo states it is not affiliated with Microsoft.
- **cookiecutter-django** (tag 2026.03.09): BSD-3-Clause; its full licence text is in [NOTICE.md](../NOTICE.md).
- **Jackcess** 5.1.7: Apache-2.0; behaviour reference only, its notice reproduced in `app/northwind/core/THIRD_PARTY.md` and NOTICE.md.
- **Chart.js** 4.5.1: MIT; vendored unchanged with its licence header, sha256 recorded in `app/northwind/reports/THIRD_PARTY.md` and NOTICE.md.
- **htmx** 2.0.10: 0BSD, inside django-htmx (MIT), installed from PyPI.
- **Microsoft ODBC Driver 18 for SQL Server** 18.6.2.2: Microsoft's proprietary licence, bundled by mssql-python through mssql-python-odbc, installed from PyPI at deploy time and never committed.
- **Runtime packages:** 65 packages listed in NOTICE.md with their licences: permissive (MIT, BSD, Apache-2.0, MPL-2.0, PSF-2.0, MIT-CMU, MIT-0), plus psycopg (LGPL-3.0-only), pyphen (GPL-2.0-or-later OR LGPL-2.1-or-later OR MPL-1.1) and text-unidecode (Artistic-1.0 OR GPL-2.0-or-later). None is in the repository; they are installed unmodified from PyPI, which their licences allow alongside MIT code.
- **Bootstrap** 5.2.3 (MIT) is loaded from cdnjs at run time and not bundled.

## Pre-flip checks

Run at the S6 demo gate in the target repository, on the merged main, with the commands of the orchestrator runbook (pipeline `docs/runbook.md` section 6, steps 3 to 9). Every check must pass before the repository is made public. The operator fills Date, Commit (`origin/main`) and Result.

| # | Check | Command | Date | Commit | Result |
|---|---|---|---|---|---|
| 1 | Fetch everything | `git -C <target repo> fetch --all --prune --tags` | 2026-10-17 | 033b23a | pass |
| 2 | Delete every remote stage branch whose pull request was merged | for each remote branch other than main: `gh pr list -R thomas-sodon/access-excel-to-django --head <branch> --state merged --json number --jq length` is at least 1, then `git -C <target repo> push origin --delete <branch>` | 2026-10-17 | 033b23a | pass: no remote stage branch left (each merge deleted its branch) |
| 3 | No unmerged branch is left | `git -C <target repo> fetch --prune && test -z "$(git -C <target repo> branch -r --no-merged origin/main)"` | 2026-10-17 | 033b23a | pass: prints nothing |
| 4 | No copied source anywhere in history | `mp-data guard /home/cloudcli/sourcecode/modernization-pipeline/engagements/northwind-demo/engagement.json --repo /home/cloudcli/sourcecode/modernization-pipeline --repo /home/cloudcli/sourcecode/access-excel-to-django --history` | 2026-10-17 | 033b23a | pass: 1,540 files, 0 failures |
| 5 | No forbidden file name ever committed | `git -C <target repo> log --all --name-only --format= \| sort -u \| grep -Ei '[.](accdt\|accdb\|accde\|mdb\|mde\|laccdb\|ldb\|mdw\|xlsm\|xlsb\|xls\|xlam\|bas\|cls\|frm\|frx\|msg\|bak\|pdf\|eml\|xlsx)$\|^(private\|data\|vendor)/'; test $? -eq 1` | 2026-10-17 | 033b23a | pass: prints nothing |
| 6 | Every GitHub Actions run of the private period deleted | `gh run list -R thomas-sodon/access-excel-to-django --limit 1000 --json databaseId --jq '.[].databaseId'`, then `gh run delete <id> -R thomas-sodon/access-excel-to-django` for each | 2026-10-17 | 033b23a | not run: the repository stays private (see Decision); run it before any future flip |
| 7 | Every pull request title, body and comment read; none mentions client material, private paths or internal notes | `gh pr list -R thomas-sodon/access-excel-to-django --state all --limit 200 --json number,title,body,comments`, fixing any with `gh pr edit <number> --body-file <file>` | 2026-10-17 | 033b23a | pass after fixes: 19 edits over PRs #1 to #7 (absolute and private paths, two possible data values, internal run notes), applied through the REST API (`gh api -X PATCH repos/thomas-sodon/access-excel-to-django/pulls/<n> -F body=@<file>`) because `gh pr edit` fails on the Projects (classic) deprecation; main commit messages carry no PR bodies |

`<target repo>` is the operator's local clone of `thomas-sodon/access-excel-to-django`, `/home/cloudcli/sourcecode/access-excel-to-django`.

## Decision

**Do not publish.** 2026-10-17, Thomas Sodon (operator): nothing is made public. The repository stays private, there is no visibility flip and no fallback public repository, and the walkthrough video is recorded locally (synthetic seed-1 data only) and not uploaded. Checks 1 to 5 and 7 passed on `033b23a`; check 6 (deleting the Actions runs of the private period) is left for a future publishing decision, which must run every check again first.
