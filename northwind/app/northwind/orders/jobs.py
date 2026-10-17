"""Scheduled jobs of the Orders, Invoicing and Shipping area
(docs/contracts.md#feature-app-contract). S6.handover documents each entry in
docs/runbook.md.

first_run is the original's start-up routine (R-orders-049, trigger schedule:startup):
run it once after each start of the application (cron's @reboot, or the deployment's
start-up hook); the first-run flag makes every run after the first do nothing.
"""

JOBS = [
    {"command": "first_run", "schedule": "@reboot", "rule": "R-orders-049"},
]
