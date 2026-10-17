"""manage.py first_run: the original's start-up job (R-orders-049, jobs.py).

On the very first run only, guarded by the first-run flag in the system settings, it
moves every date forward by the days between the latest order date and today, so
sample data looks current, then sets the flag. Changed rows are stamped System.
Prints counts only.
"""

from __future__ import annotations

import datetime as dt

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from northwind.orders import services


class Command(BaseCommand):
    help = "Run the one-off start-up date shift (R-orders-049) unless already done."

    def add_arguments(self, parser):
        parser.add_argument(
            "--today",
            help="The date to shift to, YYYY-MM-DD (default: today).",
        )

    def handle(self, *args, **options):
        today = None
        if options.get("today"):
            try:
                today = dt.datetime.strptime(options["today"], "%Y-%m-%d")  # noqa: DTZ007
            except ValueError as error:
                msg = "--today must be YYYY-MM-DD"
                raise CommandError(msg) from error
        result = services.first_run(today)
        if not result.ran:
            self.stdout.write("first_run: already done (first-run flag set)")
            return
        self.stdout.write(
            f"first_run: dates moved {result.days} days forward on {result.rows} rows",
        )
