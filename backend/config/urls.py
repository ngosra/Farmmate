from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "FarmMate"
admin.site.site_title = "FarmMate"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.urls")),
]
