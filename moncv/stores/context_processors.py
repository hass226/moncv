"""
Context processors pour améliorer le SEO et l'accessibilité
"""

from django.conf import settings


def seo_context(request):
    """Ajoute des variables SEO au contexte global"""
    return {
        'site_name': 'MYMEDAGA',
        'site_description': 'Plateforme e-commerce moderne pour jeunes entrepreneurs africains',
        'site_url': request.build_absolute_uri('/'),
        'current_url': request.build_absolute_uri(),
    }


def global_language_currency(request):
    language_code = getattr(request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE)
    currency = request.session.get('currency', 'EUR')
    return {
        'LANGUAGE_CODE': language_code,
        'current_currency': currency,
    }

