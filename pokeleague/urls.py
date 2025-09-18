from django.contrib import admin
from django.urls import path, include
from battles.sse import battle_stream

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("battles.urls")),
    path("api/battles/<int:battle_id>/stream/", battle_stream),
]