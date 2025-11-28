/**
 * Système de géolocalisation pour MYMEDAGA
 * Capture automatiquement la position du client et l'envoie via WhatsApp
 */

class GeolocationManager {
    constructor() {
        this.currentLocation = null;
        this.locationPermissionGranted = false;
        this.init();
    }

    init() {
        // Vérifier si la géolocalisation est supportée
        if (!navigator.geolocation) {
            console.warn('La géolocalisation n\'est pas supportée par ce navigateur');
            return;
        }

        // Demander la permission et obtenir la localisation au chargement
        this.requestLocation();
    }

    requestLocation() {
        const options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000 // Cache la position pendant 1 minute
        };

        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                };
                this.locationPermissionGranted = true;
                
                // Obtenir l'adresse à partir des coordonnées
                this.getAddressFromCoordinates(
                    this.currentLocation.latitude,
                    this.currentLocation.longitude
                );
                
                // Détecter le pays et ajuster la langue/devise
                if (typeof currencyConverter !== 'undefined') {
                    currencyConverter.detectCountryFromCoordinates(
                        this.currentLocation.latitude,
                        this.currentLocation.longitude
                    ).then(countryCode => {
                        if (countryCode) {
                            // Définir la devise selon le pays
                            const currency = currencyConverter.countryCurrencies[countryCode] || 'EUR';
                            localStorage.setItem('preferredCurrency', currency);
                            if (document.getElementById('currency-selector')) {
                                document.getElementById('currency-selector').value = currency;
                            }
                            updateAllPrices(currency);
                            
                            // Définir la langue selon le pays
                            const countryLanguages = {
                                'CI': 'fr', 'SN': 'fr', 'ML': 'fr', 'BF': 'fr', 'NE': 'fr', 'TG': 'fr',
                                'BJ': 'fr', 'GW': 'fr', 'GN': 'fr', 'MR': 'fr', 'CM': 'fr', 'TD': 'fr',
                                'CF': 'fr', 'GA': 'fr', 'CG': 'fr', 'CD': 'fr', 'GQ': 'fr', 'ST': 'fr',
                                'MA': 'fr', 'DZ': 'fr', 'TN': 'fr', 'FR': 'fr', 'BE': 'fr', 'CH': 'fr',
                                'NG': 'en', 'GH': 'en', 'KE': 'en', 'UG': 'en', 'TZ': 'en', 'ZA': 'en',
                                'US': 'en', 'GB': 'en', 'CA': 'en',
                            };
                            const language = countryLanguages[countryCode] || 'fr';
                            if (document.getElementById('language-selector')) {
                                document.getElementById('language-selector').value = language;
                                // Changer la langue
                                fetch('/set-language/', {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json',
                                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                                    },
                                    body: JSON.stringify({language: language})
                                });
                            }
                        }
                    });
                }
            },
            (error) => {
                console.warn('Erreur de géolocalisation:', error.message);
                this.locationPermissionGranted = false;
            },
            options
        );
    }

    async getAddressFromCoordinates(lat, lng) {
        try {
            // Utiliser l'API de géocodage inverse (Nominatim - OpenStreetMap)
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`,
                {
                    headers: {
                        'User-Agent': 'MYMEDAGA-App'
                    }
                }
            );
            
            if (response.ok) {
                const data = await response.json();
                if (data.address) {
                    const addressParts = [];
                    if (data.address.road) addressParts.push(data.address.road);
                    if (data.address.suburb || data.address.neighbourhood) {
                        addressParts.push(data.address.suburb || data.address.neighbourhood);
                    }
                    if (data.address.city || data.address.town || data.address.village) {
                        addressParts.push(data.address.city || data.address.town || data.address.village);
                    }
                    
                    this.currentLocation.address = addressParts.join(', ') || 
                        `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
                } else {
                    this.currentLocation.address = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
                }
            } else {
                this.currentLocation.address = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            }
        } catch (error) {
            console.warn('Erreur lors de la récupération de l\'adresse:', error);
            if (this.currentLocation) {
                this.currentLocation.address = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            }
        }
    }

    async getWhatsAppLinkWithLocation(productId, productName, productPrice, whatsappNumber) {
        // Toujours récupérer une nouvelle localisation pour être sûr d'avoir les données
        await new Promise((resolve) => {
            const options = {
                enableHighAccuracy: true,
                timeout: 10000, // Augmenter le timeout
                maximumAge: 0 // Toujours demander une nouvelle position
            };
            
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    this.currentLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    };
                    // Attendre que l'adresse soit récupérée
                    await this.getAddressFromCoordinates(
                        this.currentLocation.latitude,
                        this.currentLocation.longitude
                    );
                    resolve();
                },
                (error) => {
                    console.warn('Erreur géolocalisation:', error);
                    // Si erreur, on continue quand même mais sans localisation
                    this.currentLocation = null;
                    resolve();
                },
                options
            );
        });

        // Construire le message WhatsApp professionnel
        let message = `🛒 *NOUVELLE COMMANDE*\n\n`;
        message += `📦 *Produit:* ${productName}\n`;
        message += `💰 *Prix:* ${productPrice}€\n`;
        message += `\n━━━━━━━━━━━━━━━━━━━━\n`;
        
        // TOUJOURS essayer d'inclure la localisation
        if (this.currentLocation && this.currentLocation.latitude && this.currentLocation.longitude) {
            const lat = this.currentLocation.latitude;
            const lng = this.currentLocation.longitude;
            const address = this.currentLocation.address || `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            const mapsLink = `https://www.google.com/maps?q=${lat},${lng}`;
            
            message += `📍 *Localisation de livraison:*\n${address}\n\n`;
            message += `🗺️ *Voir sur la carte:*\n${mapsLink}\n`;
            message += `\n━━━━━━━━━━━━━━━━━━━━\n`;
        } else {
            // Si pas de localisation, demander au client de la fournir
            message += `📍 *Localisation:*\nVeuillez me fournir votre adresse de livraison\n`;
            message += `\n━━━━━━━━━━━━━━━━━━━━\n`;
        }
        
        message += `\n✅ Je confirme ma commande et suis disponible pour la livraison.\n`;
        message += `\nMerci de me confirmer la disponibilité et les modalités de livraison.`;

        // Utiliser le gestionnaire de numéros de téléphone pour formater correctement
        const formattedNumber = phoneNumberManager.formatForWhatsApp(whatsappNumber);
        
        // Encoder le message pour l'URL
        const encodedMessage = encodeURIComponent(message);
        
        return `https://wa.me/${formattedNumber}?text=${encodedMessage}`;
    }
}

// Initialiser le gestionnaire de géolocalisation global
const geolocationManager = new GeolocationManager();

// Fonction globale pour commander avec localisation
async function commanderAvecLocalisation(productId, productName, productPrice, whatsappNumber) {
    // Trouver le bouton cliqué et le désactiver
    const clickedButton = window.event ? window.event.target.closest('button') : null;
    if (clickedButton) {
        clickedButton.classList.add('loading');
        clickedButton.disabled = true;
    }

    // Afficher un indicateur de chargement amélioré
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'location-loading';
    loadingMessage.innerHTML = '<i class="bi bi-geo-alt"></i> <strong>Récupération de votre localisation...</strong><br><small>Veuillez autoriser l\'accès à votre position</small>';
    document.body.appendChild(loadingMessage);

    try {
        // Obtenir le lien WhatsApp avec localisation
        const whatsappUrl = await geolocationManager.getWhatsAppLinkWithLocation(
            productId,
            productName,
            productPrice,
            whatsappNumber
        );

        // Mettre à jour le message de chargement
        loadingMessage.innerHTML = '<i class="bi bi-check-circle"></i> <strong>Localisation récupérée!</strong><br><small>Ouverture de WhatsApp...</small>';
        loadingMessage.style.background = 'linear-gradient(135deg, var(--primary-green), #00A878)';

        // Attendre un peu pour que l'utilisateur voie le message
        await new Promise(resolve => setTimeout(resolve, 500));

        // Retirer le message de chargement
        loadingMessage.remove();

        // Réactiver le bouton
        if (clickedButton) {
            clickedButton.classList.remove('loading');
            clickedButton.disabled = false;
        }

        // Ouvrir WhatsApp
        window.open(whatsappUrl, '_blank');
    } catch (error) {
        console.error('Erreur lors de la commande:', error);
        
        // Mettre à jour le message d'erreur
        loadingMessage.innerHTML = '<i class="bi bi-exclamation-triangle"></i> <strong>Localisation non disponible</strong><br><small>Ouverture de WhatsApp sans localisation...</small>';
        loadingMessage.style.background = 'linear-gradient(135deg, var(--primary-orange), var(--primary-red))';
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        loadingMessage.remove();

        // Réactiver le bouton
        if (clickedButton) {
            clickedButton.classList.remove('loading');
            clickedButton.disabled = false;
        }
        
        // En cas d'erreur, utiliser le lien WhatsApp simple
        const simpleMessage = `Bonjour, je souhaite commander ${productName} (${productPrice}€).\n\nMerci de me contacter pour finaliser la commande.`;
        const formattedNumber = phoneNumberManager.formatForWhatsApp(whatsappNumber);
        const encodedMessage = encodeURIComponent(simpleMessage);
        const fallbackUrl = `https://wa.me/${formattedNumber}?text=${encodedMessage}`;
        window.open(fallbackUrl, '_blank');
    }
}

