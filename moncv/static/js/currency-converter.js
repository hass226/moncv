/**
 * Système de conversion de devises pour MYMEDAGA
 * Support de toutes les monnaies africaines et internationales
 */

class CurrencyConverter {
    constructor() {
        // Taux de change (base: EUR)
        // Note: En production, utiliser une API comme exchangerate-api.com
        this.exchangeRates = {
            'EUR': 1.0,
            'XOF': 655.957, // Franc CFA Ouest
            'XAF': 655.957, // Franc CFA Centre
            'NGN': 1600, // Naira nigérian
            'GHS': 13.5, // Cedi ghanéen
            'KES': 150, // Shilling kényan
            'ZAR': 20, // Rand sud-africain
            'EGP': 50, // Livre égyptienne
            'MAD': 11, // Dirham marocain
            'TND': 3.3, // Dinar tunisien
            'DZD': 145, // Dinar algérien
            'USD': 1.1,
            'GBP': 0.85,
            'CAD': 1.5,
            'AUD': 1.65,
            'JPY': 165,
            'CNY': 8.0,
            'INR': 92,
            'BRL': 5.5,
        };

        // Monnaies par pays
        this.countryCurrencies = {
            'CI': 'XOF', 'SN': 'XOF', 'ML': 'XOF', 'BF': 'XOF', 'NE': 'XOF', 'TG': 'XOF', 'BJ': 'XOF', 'GW': 'XOF', 'GN': 'XOF', 'MR': 'XOF',
            'CM': 'XAF', 'TD': 'XAF', 'CF': 'XAF', 'GA': 'XAF', 'CG': 'XAF', 'CD': 'XAF', 'GQ': 'XAF', 'ST': 'XAF',
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
            'JP': 'JPY',
            'CN': 'CNY',
            'IN': 'INR',
            'BR': 'BRL',
        };

        // Noms des monnaies
        this.currencyNames = {
            'EUR': 'Euro',
            'XOF': 'Franc CFA',
            'XAF': 'Franc CFA',
            'NGN': 'Naira',
            'GHS': 'Cedi',
            'KES': 'Shilling',
            'ZAR': 'Rand',
            'EGP': 'Livre égyptienne',
            'MAD': 'Dirham',
            'TND': 'Dinar',
            'DZD': 'Dinar',
            'USD': 'Dollar',
            'GBP': 'Livre',
            'CAD': 'Dollar',
            'AUD': 'Dollar',
            'JPY': 'Yen',
            'CNY': 'Yuan',
            'INR': 'Roupie',
            'BRL': 'Real',
        };

        // Symboles des monnaies
        this.currencySymbols = {
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
        };

        this.currentCurrency = 'EUR'; // Devise par défaut
        this.currentCountry = null;
    }

    /**
     * Détecte le pays à partir des coordonnées GPS
     */
    async detectCountryFromCoordinates(lat, lng) {
        try {
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=3&addressdetails=1`,
                { headers: { 'User-Agent': 'MYMEDAGA-App' } }
            );
            
            if (response.ok) {
                const data = await response.json();
                if (data.address && data.address.country_code) {
                    const countryCode = data.address.country_code.toUpperCase();
                    this.currentCountry = countryCode;
                    this.currentCurrency = this.countryCurrencies[countryCode] || 'EUR';
                    return countryCode;
                }
            }
        } catch (error) {
            console.warn('Erreur détection pays:', error);
        }
        return null;
    }

    /**
     * Convertit un prix d'une devise à une autre
     */
    convert(amount, fromCurrency, toCurrency) {
        if (fromCurrency === toCurrency) return amount;
        
        const fromRate = this.exchangeRates[fromCurrency] || 1;
        const toRate = this.exchangeRates[toCurrency] || 1;
        
        // Convertir vers EUR puis vers la devise cible
        const inEUR = amount / fromRate;
        return inEUR * toRate;
    }

    /**
     * Formate un prix avec le symbole de la devise
     */
    format(amount, currency) {
        const symbol = this.currencySymbols[currency] || currency;
        const name = this.currencyNames[currency] || currency;
        
        // Format selon la devise
        if (currency === 'XOF' || currency === 'XAF') {
            return `${Math.round(amount).toLocaleString()} ${symbol}`;
        } else if (currency === 'JPY' || currency === 'KRW') {
            return `${Math.round(amount).toLocaleString()} ${symbol}`;
        } else {
            return `${amount.toFixed(2)} ${symbol}`;
        }
    }

    /**
     * Obtient toutes les devises disponibles
     */
    getAvailableCurrencies() {
        return Object.keys(this.exchangeRates);
    }

    /**
     * Met à jour les taux de change depuis une API (optionnel)
     */
    async updateExchangeRates() {
        try {
            // Utiliser exchangerate-api.com (gratuit jusqu'à 1500 requêtes/mois)
            const response = await fetch('https://api.exchangerate-api.com/v4/latest/EUR');
            if (response.ok) {
                const data = await response.json();
                // Mettre à jour les taux pour les devises principales
                if (data.rates) {
                    Object.keys(data.rates).forEach(currency => {
                        if (this.exchangeRates.hasOwnProperty(currency)) {
                            this.exchangeRates[currency] = data.rates[currency];
                        }
                    });
                }
            }
        } catch (error) {
            console.warn('Impossible de mettre à jour les taux de change:', error);
        }
    }
}

// Instance globale
const currencyConverter = new CurrencyConverter();

// Fonction pour afficher un prix dans toutes les devises
function displayPriceInAllCurrencies(priceEUR, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const currencies = currencyConverter.getAvailableCurrencies();
    const priceHTML = currencies.map(currency => {
        const convertedPrice = currencyConverter.convert(priceEUR, 'EUR', currency);
        const formatted = currencyConverter.format(convertedPrice, currency);
        return `<span class="price-currency" data-currency="${currency}">${formatted}</span>`;
    }).join(' | ');

    container.innerHTML = priceHTML;
}

// Fonction pour afficher le prix dans la devise du pays
function displayPriceInCountryCurrency(priceEUR, countryCode) {
    const currency = currencyConverter.countryCurrencies[countryCode] || 'EUR';
    const convertedPrice = currencyConverter.convert(priceEUR, 'EUR', currency);
    return currencyConverter.format(convertedPrice, currency);
}

