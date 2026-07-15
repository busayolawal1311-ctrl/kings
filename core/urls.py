
"""Root URL configuration, including admin, storefront, auth, and development media."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("mainsite.urls")),
    path('accounts/', include('django.contrib.auth.urls')),]

if settings.DEBUG:
    # Django serves uploads only locally; production delegates media to object storage/CDN.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
