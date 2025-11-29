"""
Template tags pour l'affichage des prix dans différentes devises
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Taux de change (base: EUR)
EXCHANGE_RATES = {
    'EUR': 1.0,
    'XOF': 655.957,
    'XAF': 655.957,
    'NGN': 1600,
    'GHS': 13.5,
    'KES': 150,
    'ZAR': 20,
    'EGP': 50,
    'MAD': 11,
    'TND': 3.3,
    'DZD': 145,
    'USD': 1.1,
    'GBP': 0.85,
    'CAD': 1.5,
    'AUD': 1.65,
    'JPY': 165,
    'CNY': 8.0,
    'INR': 92,
    'BRL': 5.5,
}

CURRENCY_SYMBOLS = {
    'EUR': '€',
    'XOF': 'CFA',
    'XAF': 'FCFA',
    'NGN': '₦',
    'GHS': '₵',
    'KES': 'KSh',
    'ZAR': 'R',
    'EGP': 'E£',
    'MAD': 'DH',
    'TND': 'DT',
    'DZD': 'DA',
    'USD': '$',
    'GBP': '£',
    'CAD': 'C$',
    'AUD': 'A$',
    'JPY': '¥',
    'CNY': '¥',
    'INR': '₹',
    'BRL': 'R$',
}


@register.filter
def convert_currency(amount, currency):
    """Convertit un montant EUR vers une autre devise"""
    if not amount:
        return 0
    rate = EXCHANGE_RATES.get(currency, 1.0)
    return float(amount) * rate


@register.filter
def format_currency(amount, currency):
    """Formate un montant avec le symbole de la devise"""
    if not amount:
        return '0'
    
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    converted = convert_currency(amount, currency)
    
    # Format selon la devise
    if currency in ['XOF', 'XAF']:
        return f"{int(converted):,} {symbol}"
    elif currency in ['JPY', 'KRW']:
        return f"{int(converted):,} {symbol}"
    else:
        return f"{converted:.2f} {symbol}"


@register.simple_tag
def price_in_all_currencies(price_eur):
    """Affiche le prix dans toutes les devises disponibles"""
    currencies = ['EUR', 'XOF', 'XAF', 'NGN', 'GHS', 'KES', 'ZAR', 'USD', 'GBP']
    prices = []
    
    for currency in currencies:
        formatted = format_currency(price_eur, currency)
        prices.append(f'<span class="price-currency" data-currency="{currency}">{formatted}</span>')
    
    return mark_safe(' | '.join(prices))


@register.simple_tag
def price_in_currency(price_eur, currency='EUR'):
    """Affiche le prix dans une devise spécifique"""
    return format_currency(price_eur, currency)


@register.filter
def currency(value):
    """Filtre simple pour formater un prix (retourne juste le nombre formaté)"""
    if not value:
        return '0'
    try:
        # Formater avec séparateurs de milliers
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return str(value)


@register.filter
def split(value, delimiter=','):
    """Sépare une chaîne en liste selon un délimiteur"""
    if not value:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(str(delimiter)) if item.strip()]
    return []


@register.filter
def trim(value):
    """Supprime les espaces en début et fin"""
    if isinstance(value, str):
        return value.strip()
    return value