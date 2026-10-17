# Notices: Northwind

This file lists the third-party material in the Northwind app: the Python packages it installs at run time, the third-party files and behaviour it bundles or follows, the project template it started from, and the credit for the original application. Our own code and documents in this repository are under the MIT licence in the repository's root [LICENSE](../LICENSE); that licence covers our own work only, and everything listed here keeps its own licence.

## Runtime packages

One row per package of `uv export --frozen --no-dev --no-hashes --no-emit-project` in `app/`, with the licence from each package's installed metadata (and its licence file where the metadata is vague). These packages are installed from PyPI when the app is deployed; this repository does not contain them.

| Package | Version | Licence |
|---|---|---|
| argon2-cffi | 25.1.0 | MIT |
| argon2-cffi-bindings | 26.1.0 | MIT |
| asgiref | 3.12.1 | BSD-3-Clause |
| azure-core | 1.41.0 | MIT |
| azure-identity | 1.26.0 | MIT |
| brotli | 1.2.0 | MIT |
| brotlicffi | 1.2.0.2 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| charset-normalizer | 3.5.2 | MIT |
| colorama | 0.4.6 | BSD-3-Clause |
| crispy-bootstrap5 | 2026.9 | MIT |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| cssselect2 | 0.10.1 | BSD-3-Clause |
| diff-match-patch | 20241021 | Apache-2.0 |
| django | 5.2.18 | BSD-3-Clause |
| django-allauth | 65.19.7 | MIT |
| django-crispy-forms | 2.7 | MIT |
| django-dbbackup | 5.3.1 | BSD-3-Clause |
| django-environ | 0.13.0 | MIT |
| django-filter | 26.2 | BSD-3-Clause |
| django-htmx | 1.29.0 | MIT |
| django-import-export | 4.4.2 | BSD-2-Clause |
| django-model-utils | 5.0.0 | BSD-3-Clause |
| django-simple-history | 3.13.0 | BSD-3-Clause |
| django-tables2 | 3.0.1 | BSD-2-Clause |
| django-template-partials | 25.3 | MIT |
| django-weasyprint | 2.6.0 | Apache-2.0 |
| et-xmlfile | 2.0.0 | MIT |
| fido2 | 2.2.1 | BSD-2-Clause (some files Apache-2.0 or MPL-2.0) |
| fonttools | 4.67.0 | MIT |
| gunicorn | 25.1.0 | MIT |
| idna | 3.20 | BSD-3-Clause |
| msal | 1.39.0 | MIT |
| msal-extensions | 1.3.1 | MIT |
| mssql-django | 2.0.0 | BSD-3-Clause |
| mssql-python | 1.16.0 | MIT (its Windows driver libraries are under Microsoft licences) |
| mssql-python-odbc | 18.6.2.2 | LicenseRef-Microsoft-ODBC-Driver-18 (proprietary; see the next section) |
| mssql-python-rs | 0.3.0 | MIT |
| oauthlib | 4.0.0 | BSD-3-Clause |
| openpyxl | 3.1.5 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pillow | 12.1.1 | MIT-CMU |
| psycopg | 3.3.6 | LGPL-3.0-only |
| psycopg-binary | 3.3.6 | LGPL-3.0-only |
| pycparser | 3.11 | BSD-3-Clause |
| pydyf | 0.13.0 | BSD-3-Clause |
| pyjwt | 2.15.1 | MIT |
| pyodbc | 5.3.0 | MIT |
| pyphen | 0.18.1 | GPL-2.0-or-later OR LGPL-2.1-or-later OR MPL-1.1 |
| python-slugify | 8.0.4 | MIT |
| qrcode | 8.2 | BSD-3-Clause |
| requests | 2.34.2 | Apache-2.0 |
| sqlparse | 0.6.0 | BSD-3-Clause |
| tablib | 3.10.0 | MIT |
| text-unidecode | 1.3 | Artistic-1.0 OR GPL-2.0-or-later |
| tinycss2 | 1.5.1 | BSD-3-Clause |
| tinyhtml5 | 2.1.0 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| tzdata | 2026.5 | Apache-2.0 |
| urllib3 | 2.8.0 | MIT |
| weasyprint | 70.0 | BSD-3-Clause |
| webencodings | 0.6.1 | BSD-3-Clause |
| whitenoise | 6.12.0 | MIT |
| zopfli | 0.4.3 | Apache-2.0 |

Platform markers from the export: `brotlicffi` installs only on Python implementations other than CPython (the app runs on CPython, which uses `brotli`); `colorama` only on Windows; `psycopg-binary` and `pycparser` not on PyPy. The copyleft licences above (psycopg's LGPL, and the GPL alternatives of pyphen and text-unidecode) apply to those packages as published on PyPI: the app imports them unmodified and this repository does not redistribute them.

## Bundled third-party files

| Component | Version | Licence | Where |
|---|---|---|---|
| Jackcess | 5.1.7 | Apache-2.0 | Behaviour reference for `app/northwind/core/vbacompat.py` (Access `Format` and number-to-text rules); no Jackcess code is included. See `app/northwind/core/THIRD_PARTY.md` below. |
| htmx | 2.0.10 | 0BSD | Inside the django-htmx 1.29.0 package (`django_htmx/static/django_htmx/htmx-2.min.js`), served by its `{% htmx_script %}` tag in `app/northwind/templates/base.html`; not copied into this repository. |
| Microsoft ODBC Driver 18 for SQL Server | 18.6.2.2 | Microsoft proprietary licence (Microsoft Software License Terms for Microsoft ODBC Driver 18 for SQL Server) | Bundled by mssql-python through the mssql-python-odbc 18.6.2.2 wheel (`libmsodbcsql-18.6.so.2.1` with its licence file); installed from PyPI at deploy time, used only on SQL Server, not in this repository. |
| Chart.js | 4.5.1 | MIT | `app/northwind/reports/static/reports/vendor/chart.umd.min.js`, sha256 `48444a82d4edcb5bec0f1965faacdde18d9c17db3063d042abada2f705c9f54a`, the unchanged download of https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js (pipeline stack.app_assets.chartjs). See `app/northwind/reports/THIRD_PARTY.md` below. |

Loaded from a CDN at run time and not bundled: Bootstrap 5.2.3 (MIT), the CSS and JavaScript that `app/northwind/templates/base.html` links from cdnjs.cloudflare.com, as cookiecutter-django generates it.

## THIRD_PARTY.md files

The full text of every `THIRD_PARTY.md` under `app/`.

### app/northwind/core/THIRD_PARTY.md

````markdown
# Third-party material in core/

## Jackcess (behaviour reference for vbacompat.py)

| | |
|---|---|
| Name | Jackcess, the expression engine `io.github.spannm.jackcess.impl.expr` (`FormatUtil`, `NumberFormatter`, `DefaultFunctions`, `DefaultDateFunctions`) and `io.github.spannm.jackcess.expr` (`TemporalConfig`, `NumericConfig`) |
| Version | 5.1.7 (Maven `io.github.spannm:jackcess:5.1.7`) |
| URL | https://github.com/spannm/jackcess |
| Licence | Apache-2.0 (Apache License, Version 2.0) |
| Copyright | Copyright (c) 2016 James Ahlborn; Copyright (c) 2024 Markus Spann |
| Used in | `vbacompat.py`: the behaviour of Access's `Format` (named formats, custom date, number and text formats, how the format type is chosen, Null handling, half-even rounding), the United States date and number settings, and the number-to-text rule (15 significant digits for a Double) |

No Jackcess code is included. `vbacompat.py` is a new Python implementation, in its own
structure, of the behaviour that Jackcess's Format code implements in Java; its tests
take their expected values from Microsoft's documentation and from Jackcess's
behaviour. Where Microsoft documents a different result (minutes after an hour in a
custom date format, a two-digit exponent in the Scientific format), `vbacompat.py`
follows Microsoft.

Notice for the work this module is derived from:

```
Copyright (c) 2016 James Ahlborn
Copyright (c) 2024 Markus Spann

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
````

### app/northwind/reports/THIRD_PARTY.md

````markdown
# Third-party material in reports/

## Chart.js (the charts of the sales reports)

| | |
|---|---|
| Name | Chart.js |
| File | `static/reports/vendor/chart.umd.min.js` |
| Version | 4.5.1 |
| URL | https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js |
| sha256 | `48444a82d4edcb5bec0f1965faacdde18d9c17db3063d042abada2f705c9f54a` |
| Licence | MIT |
| Copyright | (c) 2025 Chart.js Contributors |
| Used in | `templates/reports/sales_report.html`: the monthly sales charts of the sales per employee and sales per product reports |

The file is the unchanged download of the URL above, licence header included, served
with `{% static %}`; the pages load no CDN copy.
````

## Project template

The app was generated with cookiecutter 2.7.1 from cookiecutter-django, tag `2026.03.09` (commit `47fa6ff75639865c36c797cb790b30e5b3a57a42`, https://github.com/cookiecutter/cookiecutter-django), and then extended by the modernization pipeline's overlay. The project layout, `config/settings/`, the `users` app, the account templates and `app/README.md` come from it. cookiecutter-django is under the BSD-3-Clause licence:

```
Copyright (c) 2013-2020, Daniel Roy Greenfeld
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice, this
  list of conditions and the following disclaimer in the documentation and/or
  other materials provided with the distribution.

* Neither the name of Cookiecutter Django nor the names of its contributors may
  be used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.
```

## Source credit

The original application is Microsoft's Northwind 2.0 Developer Edition, an Access database template (.accdt) that Microsoft publishes without a licence. This app uses its names and structure only: table, column, form, report and query names as identifiers, and the business behaviour paraphrased in `analysis/rules.md`. It contains none of the template's data, VBA, query, macro text or images, and this repository does not contain the template file. Microsoft, Access and Northwind are trademarks of the Microsoft group of companies; this project is not affiliated with or endorsed by Microsoft.
