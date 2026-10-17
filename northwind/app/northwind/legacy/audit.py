"""Audit stamps: the original's Before Change data macros (R-orders-031,
R-inventory-028, R-purchasing-027).

Every insert sets AddedBy, AddedOn, ModifiedBy and ModifiedOn; every update sets
ModifiedBy and ModifiedOn and keeps the stored AddedBy and AddedOn, even when the update
changes or blanks them. The name is the signed-in employee's full name (first then
last), set for the duration of a request or job with `acting_as(name)`; with nobody
signed in it is the fixed name System.

`keeping_loaded_stamps()` is for loading an existing dataset (import_dataset): rows keep
the stamps they carry, and only blank ones are filled.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterator

SYSTEM = "System"
STAMP_FIELDS = ("added_by", "added_on", "modified_by", "modified_on")

_name: ContextVar[str | None] = ContextVar("legacy_audit_name", default=None)
_keep: ContextVar[bool] = ContextVar("legacy_audit_keep", default=False)


def current_name() -> str:
    """The name stamped now: the signed-in employee's full name, else System."""
    return _name.get() or SYSTEM


@contextmanager
def acting_as(name: str | None) -> Iterator[None]:
    """Stamp `name` (an employee's "First Last") on the rows written in the block."""
    token = _name.set((name or "").strip() or None)
    try:
        yield
    finally:
        _name.reset(token)


@contextmanager
def keeping_loaded_stamps() -> Iterator[None]:
    """Keep the stamps that loaded rows already carry (dataset loads only)."""
    token = _keep.set(True)
    try:
        yield
    finally:
        _keep.reset(token)


def employee_full_name(first_name: str | None, last_name: str | None) -> str:
    """The stamp name of an employee: first name then last name."""
    return " ".join(part for part in (first_name, last_name) if part)


def stamp_time() -> dt.datetime:
    """Now, to the second (the original stores whole seconds)."""
    return timezone.now().replace(microsecond=0)


def added_by() -> models.CharField:
    return models.CharField(
        db_column="AddedBy",
        max_length=255,
        blank=True,
        null=True,
        editable=False,
    )


def added_on() -> models.DateTimeField:
    return models.DateTimeField(
        db_column="AddedOn",
        blank=True,
        null=True,
        editable=False,
    )


def modified_by() -> models.CharField:
    return models.CharField(
        db_column="ModifiedBy",
        max_length=255,
        blank=True,
        null=True,
        editable=False,
    )


def modified_on() -> models.DateTimeField:
    return models.DateTimeField(
        db_column="ModifiedOn",
        blank=True,
        null=True,
        editable=False,
    )


class AuditStampedModel(models.Model):
    """Base of every table with the four audit columns; save() applies the stamps."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        apply_stamps(self, kwargs.get("using"))
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, *STAMP_FIELDS}
        super().save(*args, **kwargs)


def apply_stamps(instance: AuditStampedModel, using: str | None = None) -> None:
    name, now = current_name(), stamp_time()
    if _keep.get():
        instance.added_by = instance.added_by or name
        instance.added_on = instance.added_on or now
        instance.modified_by = instance.modified_by or name
        instance.modified_on = instance.modified_on or now
        return
    stored = None
    if not instance._state.adding and instance.pk is not None:  # noqa: SLF001
        manager = type(instance)._base_manager  # noqa: SLF001
        stored = (
            manager.using(using or instance._state.db)  # noqa: SLF001
            .filter(pk=instance.pk)
            .values_list("added_by", "added_on")
            .first()
        )
    if stored is None:
        instance.added_by, instance.added_on = name, now
    else:
        instance.added_by, instance.added_on = stored
    instance.modified_by, instance.modified_on = name, now
