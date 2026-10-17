from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DomainConfig(AppConfig):
    """Shared calculations: no feature flag, so no URL and no nav entry."""

    name = "northwind.domain"
    label = "domain"
    verbose_name = _("Domain")
