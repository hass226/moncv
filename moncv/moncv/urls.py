"""
URL configuration for moncv project.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from stores.sitemaps import (
    StaticViewSitemap, ProductSitemap, StoreSitemap,
    JobSitemap, ClassroomSitemap, LiveStreamSitemap
)
from stores.robots import robots_txt

# Sitemaps configuration
sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
    'stores': StoreSitemap,
    'jobs': JobSitemap,
    'classrooms': ClassroomSitemap,
    'live_streams': LiveStreamSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    # URLs d'authentification
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Vos URLs personnalisées
    path('', include('stores.urls')),
    path('payments/', include('payments.urls', namespace='payments')),
    path('api/', include('stores.api_urls')),
    
    # SEO URLs
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

