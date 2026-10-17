# Notices

Third-party material and credits, one section per engagement, written at its S6 stage.

<!-- engagement:northwind-demo -->
## Northwind ([northwind/](northwind/))

- **Our code.** The code and documents written for this demo in `northwind/` are under the MIT licence in [LICENSE](LICENSE). That licence covers our own work only; the third-party material below keeps its own licence.
- **Source credit.** The names and structure of Microsoft's Northwind 2.0 Developer Edition, an Access database template that Microsoft publishes without a licence, are Microsoft's. The app uses them as names and structure only (table, column, form, report and query names, and the business behaviour paraphrased in `northwind/analysis/rules.md`); it contains none of the template's data, VBA, query or macro text, and this repository does not contain the template.
- **Trademarks.** Microsoft, Access and Northwind are trademarks of the Microsoft group of companies. This demo is not affiliated with or endorsed by Microsoft.

| Component | Licence | How the Northwind app uses it |
|---|---|---|
| cookiecutter-django | BSD-3-Clause | The app was generated from cookiecutter-django, tag 2026.03.09 (commit 47fa6ff75639865c36c797cb790b30e5b3a57a42): the project layout, settings and users app it starts from. The full licence text is in [northwind/NOTICE.md](northwind/NOTICE.md). |
| Jackcess | Apache-2.0 | Version 5.1.7, the behaviour reference for `northwind/app/northwind/core/vbacompat.py` (Access `Format` and number-to-text rules). No Jackcess code is included; its notice is in `northwind/app/northwind/core/THIRD_PARTY.md`. |
| htmx 2 | 0BSD | Version 2.0.10, inside the django-htmx package (MIT), which serves it; not copied into this repository. |
| Microsoft ODBC Driver 18 for SQL Server | Microsoft proprietary licence | Bundled by mssql-python through the mssql-python-odbc package (driver 18.6), installed from PyPI at deploy time and used only on SQL Server; not in this repository. |
| Chart.js | MIT | Version 4.5.1, vendored unchanged in `northwind/app/northwind/reports/static/reports/vendor/` for the sales report charts; its notice is in `northwind/app/northwind/reports/THIRD_PARTY.md`. |

Everything else, the 65 runtime Python packages with their versions and licences, the full text of each `THIRD_PARTY.md` and the cookiecutter-django licence, is in [northwind/NOTICE.md](northwind/NOTICE.md).
<!-- /engagement:northwind-demo -->

<!-- engagement:invoicegen-demo -->
<!-- /engagement:invoicegen-demo -->
