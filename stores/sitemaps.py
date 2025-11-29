"""
Sitemap pour améliorer le SEO de MYMEDAGA
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Store, Job, Classroom, LiveStream


class StaticViewSitemap(Sitemap):
    """Sitemap pour les pages statiques"""
    priority = 1.0
    changefreq = 'daily'
    
    def items(self):
        return [
            'home',
            'jobs_list',
            'live_streams_list',
            'classrooms_list',
        ]
    
    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    """Sitemap pour les produits"""
    changefreq = "weekly"
    priority = 0.8
    
    def items(self):
        return Product.objects.filter(is_featured=True)
    
    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else obj.created_at
    
    def location(self, obj):
        return reverse('product_detail', args=[obj.id])


class StoreSitemap(Sitemap):
    """Sitemap pour les boutiques"""
    changefreq = "weekly"
    priority = 0.9
    
    def items(self):
        return Store.objects.filter(is_verified=True)
    
    def lastmod(self, obj):
        return obj.created_at
    
    def location(self, obj):
        return reverse('store_detail', args=[obj.id])


class JobSitemap(Sitemap):
    """Sitemap pour les jobs"""
    changefreq = "daily"
    priority = 0.7
    
    def items(self):
        return Job.objects.filter(status='open')
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return reverse('job_detail', args=[obj.id])


class ClassroomSitemap(Sitemap):
    """Sitemap pour les classrooms"""
    changefreq = "weekly"
    priority = 0.6
    
    def items(self):
        return Classroom.objects.filter(is_public=True)
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return reverse('classroom_detail', args=[obj.id])


class LiveStreamSitemap(Sitemap):
    """Sitemap pour les live streams"""
    changefreq = "hourly"
    priority = 0.8
    
    def items(self):
        return LiveStream.objects.filter(status__in=['scheduled', 'live'])
    
    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else obj.created_at
    
    def location(self, obj):
        return reverse('live_stream_detail', args=[obj.id])

