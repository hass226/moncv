/**
 * Utilitaires pour la gestion des numéros de téléphone et indicatifs de pays
 * Système intelligent de détection et formatage
 */

class PhoneNumberManager {
    constructor() {
        // Base de données des indicatifs de pays (les plus courants en Afrique et international)
        this.countryCodes = {
            // Afrique de l'Ouest
            'CI': { code: '+225', name: 'Côte d\'Ivoire', flag: '🇨🇮' },
            'SN': { code: '+221', name: 'Sénégal', flag: '🇸🇳' },
            'ML': { code: '+223', name: 'Mali', flag: '🇲🇱' },
            'BF': { code: '+226', name: 'Burkina Faso', flag: '🇧🇫' },
            'NE': { code: '+227', name: 'Niger', flag: '🇳🇪' },
            'TG': { code: '+228', name: 'Togo', flag: '🇹🇬' },
            'BJ': { code: '+229', name: 'Bénin', flag: '🇧🇯' },
            'MR': { code: '+222', name: 'Mauritanie', flag: '🇲🇷' },
            'GN': { code: '+224', name: 'Guinée', flag: '🇬🇳' },
            'GW': { code: '+245', name: 'Guinée-Bissau', flag: '🇬🇼' },
            'SL': { code: '+232', name: 'Sierra Leone', flag: '🇸🇱' },
            'LR': { code: '+231', name: 'Liberia', flag: '🇱🇷' },
            'GH': { code: '+233', name: 'Ghana', flag: '🇬🇭' },
            'NG': { code: '+234', name: 'Nigeria', flag: '🇳🇬' },
            'CM': { code: '+237', name: 'Cameroun', flag: '🇨🇲' },
            'TD': { code: '+235', name: 'Tchad', flag: '🇹🇩' },
            'CF': { code: '+236', name: 'République centrafricaine', flag: '🇨🇫' },
            'GA': { code: '+241', name: 'Gabon', flag: '🇬🇦' },
            'CG': { code: '+242', name: 'Congo', flag: '🇨🇬' },
            'CD': { code: '+243', name: 'RD Congo', flag: '🇨🇩' },
            'AO': { code: '+244', name: 'Angola', flag: '🇦🇴' },
            'GQ': { code: '+240', name: 'Guinée équatoriale', flag: '🇬🇶' },
            'ST': { code: '+239', name: 'São Tomé-et-Príncipe', flag: '🇸🇹' },
            'TG': { code: '+228', name: 'Togo', flag: '🇹🇬' },
            
            // Afrique de l'Est
            'ET': { code: '+251', name: 'Éthiopie', flag: '🇪🇹' },
            'KE': { code: '+254', name: 'Kenya', flag: '🇰🇪' },
            'UG': { code: '+256', name: 'Ouganda', flag: '🇺🇬' },
            'TZ': { code: '+255', name: 'Tanzanie', flag: '🇹🇿' },
            'RW': { code: '+250', name: 'Rwanda', flag: '🇷🇼' },
            'BI': { code: '+257', name: 'Burundi', flag: '🇧🇮' },
            'DJ': { code: '+253', name: 'Djibouti', flag: '🇩🇯' },
            'SO': { code: '+252', name: 'Somalie', flag: '🇸🇴' },
            'ER': { code: '+291', name: 'Érythrée', flag: '🇪🇷' },
            
            // Afrique du Nord
            'MA': { code: '+212', name: 'Maroc', flag: '🇲🇦' },
            'DZ': { code: '+213', name: 'Algérie', flag: '🇩🇿' },
            'TN': { code: '+216', name: 'Tunisie', flag: '🇹🇳' },
            'LY': { code: '+218', name: 'Libye', flag: '🇱🇾' },
            'EG': { code: '+20', name: 'Égypte', flag: '🇪🇬' },
            'SD': { code: '+249', name: 'Soudan', flag: '🇸🇩' },
            
            // Afrique du Sud
            'ZA': { code: '+27', name: 'Afrique du Sud', flag: '🇿🇦' },
            'ZW': { code: '+263', name: 'Zimbabwe', flag: '🇿🇼' },
            'BW': { code: '+267', name: 'Botswana', flag: '🇧🇼' },
            'NA': { code: '+264', name: 'Namibie', flag: '🇳🇦' },
            'SZ': { code: '+268', name: 'Eswatini', flag: '🇸🇿' },
            'LS': { code: '+266', name: 'Lesotho', flag: '🇱🇸' },
            'MZ': { code: '+258', name: 'Mozambique', flag: '🇲🇿' },
            'MG': { code: '+261', name: 'Madagascar', flag: '🇲🇬' },
            'MU': { code: '+230', name: 'Maurice', flag: '🇲🇺' },
            'SC': { code: '+248', name: 'Seychelles', flag: '🇸🇨' },
            'KM': { code: '+269', name: 'Comores', flag: '🇰🇲' },
            
            // Autres pays importants
            'FR': { code: '+33', name: 'France', flag: '🇫🇷' },
            'US': { code: '+1', name: 'États-Unis', flag: '🇺🇸' },
            'GB': { code: '+44', name: 'Royaume-Uni', flag: '🇬🇧' },
            'BE': { code: '+32', name: 'Belgique', flag: '🇧🇪' },
            'CH': { code: '+41', name: 'Suisse', flag: '🇨🇭' },
            'CA': { code: '+1', name: 'Canada', flag: '🇨🇦' },
            'DE': { code: '+49', name: 'Allemagne', flag: '🇩🇪' },
            'IT': { code: '+39', name: 'Italie', flag: '🇮🇹' },
            'ES': { code: '+34', name: 'Espagne', flag: '🇪🇸' },
            'PT': { code: '+351', name: 'Portugal', flag: '🇵🇹' },
            'BR': { code: '+55', name: 'Brésil', flag: '🇧🇷' },
            'IN': { code: '+91', name: 'Inde', flag: '🇮🇳' },
            'CN': { code: '+86', name: 'Chine', flag: '🇨🇳' },
            'JP': { code: '+81', name: 'Japon', flag: '🇯🇵' },
            'AE': { code: '+971', name: 'Émirats arabes unis', flag: '🇦🇪' },
            'SA': { code: '+966', name: 'Arabie saoudite', flag: '🇸🇦' },
        };
    }

    /**
     * Nettoie un numéro de téléphone (enlève espaces, tirets, etc.)
     */
    cleanPhoneNumber(phone) {
        if (!phone) return '';
        return phone.toString().replace(/\s+/g, '').replace(/-/g, '').replace(/\./g, '').replace(/\(/g, '').replace(/\)/g, '');
    }

    /**
     * Détecte l'indicatif de pays dans un numéro
     */
    detectCountryCode(phone) {
        const cleaned = this.cleanPhoneNumber(phone);
        
        // Si le numéro commence déjà par +, on cherche l'indicatif
        if (cleaned.startsWith('+')) {
            // Trier les codes par longueur (du plus long au plus court) pour éviter les faux positifs
            const sortedCodes = Object.values(this.countryCodes)
                .map(c => c.code)
                .sort((a, b) => b.length - a.length);
            
            for (const code of sortedCodes) {
                if (cleaned.startsWith(code)) {
                    return code;
                }
            }
        }
        
        // Si le numéro commence par 00, remplacer par +
        if (cleaned.startsWith('00')) {
            const withPlus = '+' + cleaned.substring(2);
            return this.detectCountryCode(withPlus);
        }
        
        return null;
    }

    /**
     * Formate un numéro pour WhatsApp (international)
     */
    formatForWhatsApp(phone) {
        const cleaned = this.cleanPhoneNumber(phone);
        
        // Si déjà au bon format
        if (cleaned.startsWith('+')) {
            return cleaned.substring(1); // Enlever le + pour WhatsApp
        }
        
        // Détecter l'indicatif
        const countryCode = this.detectCountryCode(cleaned);
        
        if (countryCode) {
            // Le numéro a déjà l'indicatif
            return countryCode.substring(1) + cleaned.replace(countryCode, '').replace(/^00/, '');
        }
        
        // Si le numéro commence par 0, on peut essayer de deviner le pays
        // Pour l'instant, on retourne tel quel (l'utilisateur devra corriger)
        if (cleaned.startsWith('0')) {
            return cleaned.substring(1); // Enlever le 0 initial
        }
        
        return cleaned;
    }

    /**
     * Valide un numéro de téléphone
     */
    validatePhoneNumber(phone) {
        const cleaned = this.cleanPhoneNumber(phone);
        
        // Un numéro valide doit avoir au moins 7 chiffres et au plus 15
        const digitsOnly = cleaned.replace(/\D/g, '');
        
        if (digitsOnly.length < 7 || digitsOnly.length > 15) {
            return { valid: false, error: 'Le numéro doit contenir entre 7 et 15 chiffres' };
        }
        
        return { valid: true };
    }

    /**
     * Obtient les informations du pays à partir d'un numéro
     */
    getCountryInfo(phone) {
        const countryCode = this.detectCountryCode(phone);
        
        if (!countryCode) {
            return null;
        }
        
        for (const [country, info] of Object.entries(this.countryCodes)) {
            if (info.code === countryCode) {
                return { country, ...info };
            }
        }
        
        return null;
    }

    /**
     * Formate un numéro de manière lisible
     */
    formatReadable(phone) {
        const cleaned = this.cleanPhoneNumber(phone);
        const countryCode = this.detectCountryCode(cleaned);
        const countryInfo = this.getCountryInfo(cleaned);
        
        if (countryCode && countryInfo) {
            const numberWithoutCode = cleaned.replace(countryCode, '').replace(/^00/, '');
            return `${countryInfo.flag} ${countryCode} ${numberWithoutCode}`;
        }
        
        return cleaned;
    }
}

// Instance globale
const phoneNumberManager = new PhoneNumberManager();

// Fonction utilitaire pour formater un numéro WhatsApp
function formatWhatsAppNumber(phone) {
    return phoneNumberManager.formatForWhatsApp(phone);
}

// Fonction pour obtenir un lien WhatsApp formaté
function getWhatsAppLink(phone, message = '') {
    const formattedNumber = formatWhatsAppNumber(phone);
    const encodedMessage = encodeURIComponent(message);
    return `https://wa.me/${formattedNumber}${message ? '?text=' + encodedMessage : ''}`;
}

