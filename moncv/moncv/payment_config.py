# Configuration des paiements MYMEDAGA

# Orange Money
ORANGE_MONEY_NUMBER = "+22604647641"

# Wave (Mobile Money)
WAVE_NUMBER = "58485509"

# Instructions de paiement
PAYMENT_INSTRUCTIONS = {
    'orange_money': {
        'name': 'Orange Money',
        'number': ORANGE_MONEY_NUMBER,
        'instructions': f'Composez *144# puis sélectionnez "Payer" et entrez le numéro {ORANGE_MONEY_NUMBER}'
    },
    'moov_money': {
        'name': 'Moov Money',
        'number': '+22604647641',
        'instructions': 'Composez *155# puis sélectionnez "Payer" et entrez le numéro MYMEDAGA'
    },
    'mobile_money': {
        'name': 'Mobile Money',
        'number': WAVE_NUMBER,
        'instructions': f'Utilisez votre application Mobile Money et envoyez à {WAVE_NUMBER}'
    },
    'wave': {
        'name': 'Wave',
        'number': WAVE_NUMBER,
        'instructions': f'Utilisez l\'application Wave et envoyez à {WAVE_NUMBER}'
    },
    'card': {
        'name': 'Carte Bancaire',
        'instructions': 'Utilisez le formulaire de paiement sécurisé ci-dessous'
    },
    'paypal': {
        'name': 'PayPal',
        'instructions': 'Connectez-vous à votre compte PayPal pour finaliser le paiement'
    }
}

