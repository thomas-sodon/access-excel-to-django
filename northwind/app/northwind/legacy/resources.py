"""django-import-export resources for the kept tables
(docs/contracts.md#feature-app-contract).

RESOURCES maps each model's `db_table` (the original table name) to its ModelResource.
Every field keeps the model's attribute name and takes the original column name as
`column_name`, so a dataset CSV (header = the original column names) imports unchanged
and an export writes the same header. Foreign keys import and export the referenced key
value. The key column is the import id.
"""

from __future__ import annotations

from django.apps import apps
from import_export import resources


class LegacyResource(resources.ModelResource):
    """Columns named as in the original table."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for django_field in self._meta.model._meta.concrete_fields:  # noqa: SLF001
            field = self.fields.get(django_field.name)
            if field is not None:
                field.column_name = django_field.column


def resource_for(model) -> type[LegacyResource]:
    """The ModelResource of one legacy model: every column, in table order."""
    opts = model._meta  # noqa: SLF001
    names = tuple(f.name for f in opts.concrete_fields)
    meta = type(
        "Meta",
        (),
        {
            "model": model,
            "fields": names,
            "export_order": names,
            "import_id_fields": (opts.pk.name,),
            "skip_unchanged": False,
        },
    )
    return type(f"{model.__name__}Resource", (LegacyResource,), {"Meta": meta})


def legacy_models() -> list:
    """The kept-table models (the history models excluded), in name order."""
    return sorted(
        (
            m
            for m in apps.get_app_config("legacy").get_models()
            if not m.__name__.startswith("Historical")
        ),
        key=lambda m: m._meta.db_table,  # noqa: SLF001
    )


RESOURCES: dict[str, type[LegacyResource]] = {
    model._meta.db_table: resource_for(model)  # noqa: SLF001
    for model in legacy_models()
}
