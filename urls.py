from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.views.generic import TemplateView
urlpatterns += [
    path("health/", __import__("api.health", fromlist=["health"]).health),
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
]
