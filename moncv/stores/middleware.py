"""
Middleware pour détecter la langue et la devise selon le pays
"""

class LanguageCurrencyMiddleware:
    """
    Détecte la langue et la devise selon le pays de l'utilisateur
    """
    
    # Mapping pays -> langue
    COUNTRY_LANGUAGES = {
        # Pays francophones
        'CI': 'fr', 'SN': 'fr', 'ML': 'fr', 'BF': 'fr', 'NE': 'fr', 'TG': 'fr', 
        'BJ': 'fr', 'GW': 'fr', 'GN': 'fr', 'MR': 'fr', 'CM': 'fr', 'TD': 'fr', 
        'CF': 'fr', 'GA': 'fr', 'CG': 'fr', 'CD': 'fr', 'GQ': 'fr', 'ST': 'fr',
        'MA': 'fr', 'DZ': 'fr', 'TN': 'fr', 'FR': 'fr', 'BE': 'fr', 'CH': 'fr',
        # Pays anglophones
        'NG': 'en', 'GH': 'en', 'KE': 'en', 'UG': 'en', 'TZ': 'en', 'RW': 'en',
        'BI': 'en', 'DJ': 'en', 'SO': 'en', 'ER': 'en', 'ET': 'en',
        'ZA': 'en', 'ZW': 'en', 'BW': 'en', 'NA': 'en', 'SZ': 'en', 'LS': 'en',
        'MZ': 'en', 'MG': 'en', 'MU': 'en', 'SC': 'en', 'KM': 'en',
        'US': 'en', 'GB': 'en', 'CA': 'en', 'AU': 'en', 'NZ': 'en',
        # Autres
        'EG': 'en', 'SD': 'en', 'LY': 'en',
    }
    
    # Mapping pays -> devise
    COUNTRY_CURRENCIES = {
        'CI': 'XOF', 'SN': 'XOF', 'ML': 'XOF', 'BF': 'XOF', 'NE': 'XOF', 'TG': 'XOF', 
        'BJ': 'XOF', 'GW': 'XOF', 'GN': 'XOF', 'MR': 'XOF',
        'CM': 'XAF', 'TD': 'XAF', 'CF': 'XAF', 'GA': 'XAF', 'CG': 'XAF', 'CD': 'XAF', 
        'GQ': 'XAF', 'ST': 'XAF',
        'NG': 'NGN',
        'GH': 'GHS',
        'KE': 'KES', 'UG': 'KES', 'TZ': 'KES',
        'ZA': 'ZAR', 'BW': 'ZAR', 'NA': 'ZAR', 'SZ': 'ZAR', 'LS': 'ZAR',
        'EG': 'EGP', 'SD': 'EGP',
        'MA': 'MAD',
        'TN': 'TND',
        'DZ': 'DZD',
        'FR': 'EUR', 'BE': 'EUR', 'CH': 'EUR',
        'US': 'USD', 'CA': 'USD',
        'GB': 'GBP',
    }
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Détecter la langue depuis la session ou l'en-tête Accept-Language
        if 'language' not in request.session:
            # Détecter depuis l'en-tête Accept-Language
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            if 'en' in accept_language.lower():
                request.session['language'] = 'en'
            else:
                request.session['language'] = 'fr'
        
        # Détecter la devise depuis la session
        if 'currency' not in request.session:
            # Essayer de déduire le pays depuis l'en-tête Accept-Language
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            country_code = None
            if accept_language:
                # Exemple d'en-tête : "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
                first_lang = accept_language.split(',')[0].strip()
                # On récupère la partie pays s'il y en a une (fr-FR -> FR)
                parts = first_lang.split(';')[0].split('-')
                if len(parts) == 2:
                    country_code = parts[1].upper()

            if country_code and country_code in self.COUNTRY_CURRENCIES:
                request.session['currency'] = self.COUNTRY_CURRENCIES[country_code]
            else:
                # Par défaut EUR
                request.session['currency'] = 'EUR'
        
        # Appliquer la langue
        from django.utils import translation
        language = request.session.get('language', 'fr')
        translation.activate(language)
        request.LANGUAGE_CODE = language
        
        response = self.get_response(request)
        
        translation.deactivate()
        
        return response

