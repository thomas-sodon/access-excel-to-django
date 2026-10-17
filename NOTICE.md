# Notices

This repository holds demo engagements of the modernization pipeline: each folder rebuilds one legacy Office application as a Django app. This file credits third-party material; each app folder's `NOTICE.md` has the full detail.

## Our code

The code and documents written for these demos are under the MIT licence in [LICENSE](LICENSE). That licence covers our own work only. Third-party material keeps its own licence, listed below and in each app's `NOTICE.md`.

## Third-party material in every app

| Component | Licence | How it is used |
|---|---|---|
| cookiecutter-django | BSD-3-Clause | Each app was generated from cookiecutter-django, tag 2026.03.09 (commit 47fa6ff75639865c36c797cb790b30e5b3a57a42): the project layout, settings and users app it starts from. The full licence text is in each app's `NOTICE.md`. |
| Jackcess | Apache-2.0 | Version 5.1.7, the behaviour reference for `core/vbacompat.py` (Access `Format` and number-to-text rules). No Jackcess code is included; its notice is in `core/THIRD_PARTY.md`. |
| htmx 2 | 0BSD | Version 2.0.10, inside the django-htmx package (MIT), which serves it; not copied into this repository. |
| Microsoft ODBC Driver 18 for SQL Server | Microsoft proprietary licence | Bundled by mssql-python through the mssql-python-odbc package (driver 18.6), installed from PyPI at deploy time for SQL Server; not in this repository. |

Each app's `NOTICE.md` lists its runtime Python packages with their versions and licences, the third-party files it bundles, and the full text of every `THIRD_PARTY.md` in its code.

<!-- engagement:northwind-demo -->
## Northwind ([northwind/](northwind/))

- **Source credit.** The names and structure of Microsoft's Northwind 2.0 Developer Edition, an Access database template that Microsoft publishes without a licence, are Microsoft's. The app uses them as names and structure only (table, column, form, report and query names, and the business behaviour paraphrased in `northwind/analysis/rules.md`); it contains none of the template's data, VBA, query or macro text, and this repository does not contain the template.
- **Trademarks.** Microsoft, Access and Northwind are trademarks of the Microsoft group of companies. This demo is not affiliated with or endorsed by Microsoft.
- **Bundled files.** Chart.js 4.5.1 (MIT), vendored unchanged in `northwind/app/northwind/reports/static/reports/vendor/` for the sales report charts.
- **Everything else** (65 runtime packages, the THIRD_PARTY.md texts, the cookiecutter-django licence): [northwind/NOTICE.md](northwind/NOTICE.md).
<!-- /engagement:northwind-demo -->

<!-- engagement:invoicegen-demo -->
<!-- /engagement:invoicegen-demo -->
