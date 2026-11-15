"""URLs for the health app."""
from django.urls import path

from health.views import HealthView

urlpatterns = [
    path("healthz", HealthView.as_view(), name="healthz"),
]
