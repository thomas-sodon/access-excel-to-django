"""Every legacy model has a factory whose rows save and pass full_clean()."""

import pytest

from northwind.legacy.factories import FACTORIES
from northwind.legacy.resources import legacy_models

pytestmark = pytest.mark.django_db

MODELS = sorted(FACTORIES, key=lambda m: m.__name__)


def test_every_model_has_a_factory():
    assert set(FACTORIES) == set(legacy_models())


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_factory_saves_and_passes_full_clean(model):
    first = FACTORIES[model].create()
    second = FACTORIES[model].create()
    for obj in (first, second):
        obj.refresh_from_db()
        obj.full_clean()
        assert obj.history.exists()
    assert model.objects.filter(pk=first.pk).exists()
