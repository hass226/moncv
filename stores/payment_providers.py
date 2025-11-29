"""
Système de paiement mobile pour MYMEDAGA
Intégration avec les API officielles des fournisseurs
"""

import requests
import json
import hashlib
import hmac
from datetime import datetime
from django.conf import settings
from django.utils import timezone
import logging
import paydunya
from paydunya import Store, Invoice
from .paydunya_service import configure_paydunya

logger = logging.getLogger(__name__)


class PaymentProvider:
    """Classe de base pour les fournisseurs de paiement"""
    
    def __init__(self, api_key, api_secret, merchant_id=None, environment='production'):
        self.api_key = api_key
        self.api_secret = api_secret
        self.merchant_id = merchant_id
        self.environment = environment
        self.base_url = self.get_base_url()
    
    def get_base_url(self):
        """Retourne l'URL de base selon l'environnement"""
        raise NotImplementedError
    
    def generate_signature(self, data):
        """Génère la signature pour l'authentification"""
        raise NotImplementedError
    
    def initiate_payment(self, amount, phone_number, transaction_id, description="", currency="XOF"):
        """Initie un paiement"""
        raise NotImplementedError
    
    def verify_payment(self, transaction_id):
        """Vérifie le statut d'une transaction"""
        raise NotImplementedError


class OrangeMoneyProvider(PaymentProvider):
    """Intégration Orange Money API"""
    
    def get_base_url(self):
        if self.environment == 'production':
            return 'https://api.orange.com/orange-money-webpay'
        else:
            return 'https://api.orange.com/orange-money-webpay/dev/v1'
    
    def generate_signature(self, data):
        """Génère la signature HMAC-SHA256"""
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def initiate_payment(self, amount, phone_number, transaction_id, description=""):
        """
        Initie un paiement Orange Money
        
        Documentation: https://developer.orange.com/apis/orange-money-webpay/
        """
        try:
            # Nettoyer le numéro de téléphone
            phone = phone_number.replace(' ', '').replace('-', '').replace('+', '')
            if phone.startswith('00'):
                phone = phone[2:]
            elif phone.startswith('0'):
                phone = '225' + phone[1:]  # Code pays Côte d'Ivoire par défaut
            
            # Préparer les données
            payment_data = {
                "merchant_key": self.api_key,
                "currency": "XOF",
                "order_id": transaction_id,
                "amount": str(int(float(amount) * 100)),  # Montant en centimes
                "return_url": f"{settings.SITE_URL}/payment/callback/",
                "cancel_url": f"{settings.SITE_URL}/payment/cancel/",
                "notif_url": f"{settings.SITE_URL}/payment/webhook/orange/",
                "lang": "fr",
                "reference": description[:50] if description else transaction_id
            }
            
            # Générer la signature
            signature = self.generate_signature(payment_data)
            payment_data['signature'] = signature
            
            # Headers
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Faire la requête
            response = requests.post(
                f'{self.base_url}/cashin',
                json=payment_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'payment_url': data.get('payment_url'),
                    'transaction_id': transaction_id,
                    'status': 'pending',
                    'provider_response': data
                }
            else:
                logger.error(f"Orange Money API Error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Erreur API: {response.status_code}",
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"Orange Money Payment Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class CinetPayProvider(PaymentProvider):
    """Intégration générique CinetPay (stub configurable plus tard)"""

    def get_base_url(self):
        if self.environment == 'production':
            return 'https://api-checkout.cinetpay.com'
        return 'https://api-checkout.cinetpay.com'  # Sandbox utilise souvent la même base avec des clés test

    def generate_signature(self, data):
        """Signature simple HMAC-SHA256 sur le payload.

        La signature réelle dépendra de la doc CinetPay, ceci est un stub.
        """
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def initiate_payment(self, amount, phone_number, transaction_id, description="", currency=None):
        """Initie un paiement CinetPay de manière générique.

        Si les clés ne sont pas configurées, renvoie une erreur explicite.
        """
        if not self.api_key or not self.merchant_id:
            return {
                'success': False,
                'error': "CinetPay n'est pas encore configuré (API_KEY / SITE_ID manquants).",
            }

        try:
            # Si aucune devise n'est fournie, on reste sur XOF par défaut
            currency = currency or "XOF"

            payload = {
                'apikey': self.api_key,
                'site_id': self.merchant_id,
                'transaction_id': transaction_id,
                'amount': float(amount),
                'currency': currency,
                'description': description or f'Paiement {transaction_id}',
                'return_url': f"{settings.SITE_URL}/payment/{transaction_id}/status/",
                'notify_url': f"{settings.SITE_URL}/payment/webhook/cinetpay/",
            }

            # Signature générique (à adapter avec la doc réelle)
            payload['signature'] = self.generate_signature(payload)

            response = requests.post(
                f'{self.base_url}/v2/payment',
                json=payload,
                timeout=30,
            )

            if response.status_code in [200, 201]:
                data = response.json()
                payment_url = data.get('data', {}).get('payment_url') if isinstance(data, dict) else ''
                return {
                    'success': True,
                    'payment_url': payment_url,
                    'transaction_id': transaction_id,
                    'status': 'pending',
                    'provider_response': data,
                }

            logger.error(f"CinetPay API Error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f"Erreur API CinetPay: {response.status_code}",
                'details': response.text,
            }

        except Exception as e:
            logger.error(f"CinetPay Payment Error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def verify_payment(self, transaction_id):
        """Stub de vérification de paiement CinetPay.

        À adapter avec l'endpoint de vérification officiel plus tard.
        """
        return {
            'success': True,
            'status': 'pending',
            'transaction_id': transaction_id,
            'provider_response': {},
        }


class PayPalProvider(PaymentProvider):
    """Intégration basique PayPal Checkout (REST API v2).

    Cette implémentation crée simplement un "order" PayPal et renvoie
    l'URL d'approbation pour rediriger le client. La validation finale
    doit être faite côté serveur via un webhook ou un endpoint séparé.
    """

    def get_base_url(self):
        # Sandbox ou production selon l'environnement
        if self.environment == 'production':
            return 'https://api-m.paypal.com'
        return 'https://api-m.sandbox.paypal.com'

    def generate_signature(self, data):  # non utilisé pour PayPal
        return ''

    def _get_access_token(self):
        """Obtient un access token OAuth2 PayPal à partir du client_id/secret.

        On utilise api_key comme client_id et api_secret comme secret.
        """
        try:
            auth = (self.api_key, self.api_secret)
            response = requests.post(
                f'{self.base_url}/v1/oauth2/token',
                data={'grant_type': 'client_credentials'},
                auth=auth,
                timeout=30,
            )
            if response.status_code in (200, 201):
                return response.json().get('access_token')
            logger.error(f"PayPal OAuth error: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            logger.error(f"PayPal OAuth exception: {str(e)}", exc_info=True)
            return None

    def initiate_payment(self, amount, phone_number, transaction_id, description="", currency="EUR"):
        """Crée un ordre PayPal et renvoie l'URL d'approbation.

        amount: montant décimal
        currency: devise (par défaut EUR, à adapter selon ton projet)
        """
        if not self.api_key or not self.api_secret:
            return {
                'success': False,
                'error': "PayPal n'est pas encore configuré (CLIENT_ID / SECRET manquants).",
            }

        access_token = self._get_access_token()
        if not access_token:
            return {
                'success': False,
                'error': "Impossible d'obtenir un access token PayPal.",
            }

        try:
            payload = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": transaction_id,
                        "amount": {
                            "currency_code": currency,
                            "value": f"{float(amount):.2f}",
                        },
                        "description": description or f"Paiement {transaction_id}",
                    }
                ],
                "application_context": {
                    "return_url": f"{settings.SITE_URL}/payment/paypal/return/?transaction_id={transaction_id}",
                    "cancel_url": f"{settings.SITE_URL}/payment/cancel/",
                },
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
            }

            response = requests.post(
                f'{self.base_url}/v2/checkout/orders',
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code in (200, 201):
                data = response.json()
                approval_url = ''
                for link in data.get('links', []):
                    if link.get('rel') == 'approve':
                        approval_url = link.get('href', '')
                        break

                if not approval_url:
                    return {
                        'success': False,
                        'error': "Réponse PayPal sans URL d'approbation.",
                        'provider_response': data,
                    }

                return {
                    'success': True,
                    'payment_url': approval_url,
                    'transaction_id': transaction_id,
                    'status': 'pending',
                    'provider_response': data,
                }

            logger.error(f"PayPal create order error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f"Erreur API PayPal: {response.status_code}",
                'details': response.text,
            }
        except Exception as e:
            logger.error(f"PayPal Payment Error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def verify_payment(self, transaction_id):
        """Stub de vérification PayPal.

        En pratique, il faudrait appeler l'API /v2/checkout/orders/{id}
        ou traiter un webhook. Ici on renvoie simplement pending.
        """
        return {
            'success': True,
            'status': 'pending',
            'transaction_id': transaction_id,
            'provider_response': {},
        }


class StripeProvider(PaymentProvider):
    """Intégration générique Stripe (stub configurable plus tard).

    Cette classe se contente de vérifier la présence de STRIPE_SECRET_KEY.
    L'intégration complète (Checkout Session, PaymentIntent, etc.) pourra être ajoutée ensuite.
    """

    def get_base_url(self):
        # Stripe utilise une base unique, la distinction test/production se fait par la clé
        return 'https://api.stripe.com'

    def generate_signature(self, data):
        # Non utilisé ici, Stripe a son propre système de signature de webhook
        return ''

    def initiate_payment(self, amount, phone_number, transaction_id, description=""):
        """Initie un paiement Stripe de manière générique.

        Pour l'instant, renvoie une erreur si STRIPE_SECRET_KEY est vide.
        """
        if not self.api_key:
            return {
                'success': False,
                'error': "Stripe n'est pas encore configuré (STRIPE_SECRET_KEY manquante).",
            }

        # Implémentation future : création de Checkout Session ou PaymentIntent.
        # Ici on renvoie simplement une erreur contrôlée pour éviter les appels réels.
        return {
            'success': False,
            'error': "Stripe est configuré, mais l'intégration Checkout n'est pas encore implémentée.",
        }

    def verify_payment(self, transaction_id):
        """Stub de vérification Stripe.

        En pratique, la validation se fait via le webhook et/ou les endpoints PaymentIntent.
        """
        return {
            'success': True,
            'status': 'pending',
            'transaction_id': transaction_id,
            'provider_response': {},
        }

class PayDunyaProvider(PaymentProvider):
    """Intégration PayDunya via la librairie officielle"""

    def get_base_url(self):
        # Géré par la SDK PayDunya, pas besoin d'URL ici
        return ''

    def generate_signature(self, data):
        # Non utilisé avec la SDK Python PayDunya
        return ''

    def initiate_payment(self, amount, phone_number, transaction_id, description=""):
        """Initie un paiement PayDunya en créant une CheckoutInvoice"""
        try:
            configure_paydunya()
            # Créer le store PayDunya (nom minimal)
            store = Store(name='CampusCommerce')

            invoice = Invoice(store)

            # Montant attendu par PayDunya en XOF (int)
            amount_fcfa = int(float(amount))
            invoice.total_amount = amount_fcfa

            if description:
                invoice.description = description

            # Créer la facture côté PayDunya
            successful, response = invoice.create()

            if successful:
                invoice_data = response.get('invoice', {}) if isinstance(response, dict) else {}
                payment_url = invoice_data.get('url') or invoice_data.get('secure_url') or ''

                return {
                    'success': True,
                    'payment_url': payment_url,
                    'transaction_id': transaction_id,
                    'status': 'pending',
                    'provider_response': response,
                }
            else:
                error_msg = response.get('response_text') if isinstance(response, dict) else str(response)
                logger.error(f"PayDunya API Error: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg or 'Erreur inconnue PayDunya',
                    'details': response,
                }

        except Exception as e:
            logger.error(f"PayDunya Payment Error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }

    def verify_payment(self, transaction_id):
        """Vérification optionnelle via PayDunya.

        Dans cette implémentation simple, on renvoie 'pending' et on compte
        sur le webhook PayDunya pour marquer la commande comme payée.
        """
        return {
            'success': True,
            'status': 'pending',
            'transaction_id': transaction_id,
            'provider_response': {},
        }
    
    def verify_payment(self, transaction_id):
        """Vérifie le statut d'une transaction Orange Money"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'{self.base_url}/transaction/{transaction_id}',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                return {
                    'success': True,
                    'status': 'completed' if status == 'SUCCESS' else 'pending',
                    'transaction_id': transaction_id,
                    'provider_response': data
                }
            else:
                return {
                    'success': False,
                    'error': f"Erreur vérification: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Orange Money Verification Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class FedaPayProvider(PaymentProvider):
    """Intégration FedaPay (stub de base).

    Cette classe est prévue pour être complétée avec la vraie API FedaPay.
    Pour l'instant, elle vérifie simplement que les clés sont configurées
    et renvoie une erreur contrôlée pour éviter tout appel externe non maîtrisé.
    """

    def get_base_url(self):
        # À adapter avec l'URL officielle sandbox / production de FedaPay
        if self.environment == 'production':
            return 'https://api.fedapay.com'
        return 'https://sandbox-api.fedapay.com'

    def generate_signature(self, data):
        # La vraie signature dépend de la doc FedaPay
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def initiate_payment(self, amount, phone_number, transaction_id, description="", currency="XOF"):
        """Initie un paiement FedaPay (implémentation à compléter).

        Pour éviter de casser la prod, on renvoie pour l'instant une erreur
        explicite si les clés ne sont pas configurées ou si l'intégration
        complète n'a pas encore été faite.
        """
        if not self.api_key:
            return {
                'success': False,
                'error': "FedaPay n'est pas encore configuré (FEDAPAY_API_KEY manquante).",
            }

        # TODO: Implémenter l'appel réel à l'API FedaPay à partir de la doc officielle.
        return {
            'success': False,
            'error': "FedaPay est configuré, mais l'intégration API n'est pas encore implémentée.",
        }

    def verify_payment(self, transaction_id):
        """Stub de vérification FedaPay.

        En pratique, la validation devrait se faire via le webhook FedaPay
        ou un endpoint de vérification. Ici on renvoie simplement 'pending'.
        """
        return {
            'success': True,
            'status': 'pending',
            'transaction_id': transaction_id,
            'provider_response': {},
        }


class PaystackProvider(PaymentProvider):
    """Intégration Paystack Mobile Money (stub de base).

    À compléter avec l'API Paystack (checkout, mobile money).
    Pour l'instant, on vérifie juste la présence des clés et on renvoie
    une erreur contrôlée pour éviter les appels non maîtrisés.
    """

    def get_base_url(self):
        # À adapter si Paystack a une URL sandbox distincte
        if self.environment == 'production':
            return 'https://api.paystack.co'
        return 'https://api.paystack.co'

    def generate_signature(self, data):
        # Paystack utilise généralement des headers d'authentification Bearer,
        # la signature ici est un simple HMAC générique si besoin.
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def initiate_payment(self, amount, phone_number, transaction_id, description="", currency="XOF"):
        """Initie un paiement Paystack (implémentation à compléter).

        Renvoie une erreur contrôlée tant que l'intégration complète
        n'est pas codée et/ou les clés ne sont pas configurées.
        """
        if not self.api_key:
            return {
                'success': False,
                'error': "Paystack n'est pas encore configuré (PAYSTACK_SECRET_KEY manquante).",
            }

        # TODO: Implémenter la création de transaction Paystack (mobile money / carte)
        # en suivant la documentation officielle.
        return {
            'success': False,
            'error': "Paystack est configuré, mais l'intégration API n'est pas encore implémentée.",
        }

    def verify_payment(self, transaction_id):
        """Stub de vérification Paystack.

        À remplacer par un appel à l'endpoint de vérification Paystack.
        """
        return {
            'success': True,
            'status': 'pending',
            'transaction_id': transaction_id,
            'provider_response': {},
        }


class MoovMoneyProvider(PaymentProvider):
    """Intégration Moov Money API"""
    
    def get_base_url(self):
        if self.environment == 'production':
            return 'https://api.moov-africa.com/v1'
        else:
            return 'https://api-sandbox.moov-africa.com/v1'
    
    def generate_signature(self, data):
        """Génère la signature pour Moov Money"""
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def initiate_payment(self, amount, phone_number, transaction_id, description=""):
        """Initie un paiement Moov Money"""
        try:
            phone = phone_number.replace(' ', '').replace('-', '').replace('+', '')
            if phone.startswith('00'):
                phone = phone[2:]
            elif phone.startswith('0'):
                phone = '229' + phone[1:]  # Code pays Bénin par défaut
            
            payment_data = {
                "merchantId": self.merchant_id,
                "amount": float(amount),
                "currency": "XOF",
                "orderId": transaction_id,
                "customerPhone": phone,
                "description": description or f"Paiement {transaction_id}",
                "callbackUrl": f"{settings.SITE_URL}/payment/webhook/moov/"
            }
            
            signature = self.generate_signature(payment_data)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'X-Signature': signature,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'{self.base_url}/payments/initiate',
                json=payment_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    'success': True,
                    'payment_url': data.get('paymentUrl'),
                    'transaction_id': transaction_id,
                    'status': 'pending',
                    'provider_response': data
                }
            else:
                logger.error(f"Moov Money API Error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Erreur API: {response.status_code}",
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"Moov Money Payment Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, transaction_id):
        """Vérifie le statut d'une transaction Moov Money"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'{self.base_url}/payments/{transaction_id}',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                return {
                    'success': True,
                    'status': 'completed' if status == 'SUCCESS' else 'pending',
                    'transaction_id': transaction_id,
                    'provider_response': data
                }
            else:
                return {
                    'success': False,
                    'error': f"Erreur vérification: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Moov Money Verification Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class MTNMoneyProvider(PaymentProvider):
    """Intégration MTN Mobile Money API"""
    
    def get_base_url(self):
        if self.environment == 'production':
            return 'https://api.momodeveloper.mtn.com'
        else:
            return 'https://sandbox.momodeveloper.mtn.com'
    
    def generate_signature(self, data):
        """Génère la signature pour MTN"""
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def initiate_payment(self, amount, phone_number, transaction_id, description=""):
        """Initie un paiement MTN Mobile Money"""
        try:
            phone = phone_number.replace(' ', '').replace('-', '').replace('+', '')
            if phone.startswith('00'):
                phone = phone[2:]
            elif phone.startswith('0'):
                phone = '237' + phone[1:]  # Code pays Cameroun par défaut
            
            # Obtenir le token d'accès
            token = self.get_access_token()
            if not token:
                return {
                    'success': False,
                    'error': 'Impossible d\'obtenir le token d\'accès'
                }
            
            payment_data = {
                "amount": str(amount),
                "currency": "XAF",
                "externalId": transaction_id,
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone
                },
                "payerMessage": description or f"Paiement {transaction_id}",
                "payeeNote": f"Commande {transaction_id}"
            }
            
            headers = {
                'Authorization': f'Bearer {token}',
                'X-Target-Environment': 'production' if self.environment == 'production' else 'sandbox',
                'Content-Type': 'application/json',
                'X-Reference-Id': transaction_id
            }
            
            response = requests.post(
                f'{self.base_url}/collection/v1_0/requesttopay',
                json=payment_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 202]:
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'status': 'pending',
                    'provider_response': {'status': 'PENDING'}
                }
            else:
                logger.error(f"MTN API Error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Erreur API: {response.status_code}",
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"MTN Payment Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_access_token(self):
        """Obtient le token d'accès MTN"""
        try:
            auth_string = f"{self.api_key}:{self.api_secret}"
            import base64
            auth_header = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_header}'
            }
            
            response = requests.post(
                f'{self.base_url}/collection/token/',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('access_token')
            return None
        except Exception as e:
            logger.error(f"MTN Token Error: {str(e)}")
            return None
    
    def verify_payment(self, transaction_id):
        """Vérifie le statut d'une transaction MTN"""
        try:
            token = self.get_access_token()
            if not token:
                return {
                    'success': False,
                    'error': 'Impossible d\'obtenir le token'
                }
            
            headers = {
                'Authorization': f'Bearer {token}',
                'X-Target-Environment': 'production' if self.environment == 'production' else 'sandbox'
            }
            
            response = requests.get(
                f'{self.base_url}/collection/v1_0/requesttopay/{transaction_id}',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                return {
                    'success': True,
                    'status': 'completed' if status == 'SUCCESSFUL' else 'pending',
                    'transaction_id': transaction_id,
                    'provider_response': data
                }
            else:
                return {
                    'success': False,
                    'error': f"Erreur vérification: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"MTN Verification Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class WaveProvider(PaymentProvider):
    """Intégration Wave API"""
    
    def get_base_url(self):
        if self.environment == 'production':
            return 'https://api.wave.com/v1'
        else:
            return 'https://api-sandbox.wave.com/v1'
    
    def generate_signature(self, data):
        """Génère la signature pour Wave"""
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def initiate_payment(self, amount, phone_number, transaction_id, description=""):
        """Initie un paiement Wave"""
        try:
            payment_data = {
                "amount": float(amount),
                "currency": "XOF",
                "reference": transaction_id,
                "description": description or f"Paiement {transaction_id}",
                "callback_url": f"{settings.SITE_URL}/payment/webhook/wave/"
            }
            
            signature = self.generate_signature(payment_data)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'X-Signature': signature,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'{self.base_url}/checkout/initialize',
                json=payment_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    'success': True,
                    'payment_url': data.get('checkout_url'),
                    'transaction_id': transaction_id,
                    'status': 'pending',
                    'provider_response': data
                }
            else:
                logger.error(f"Wave API Error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Erreur API: {response.status_code}",
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"Wave Payment Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, transaction_id):
        """Vérifie le statut d'une transaction Wave"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'{self.base_url}/checkout/{transaction_id}',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                return {
                    'success': True,
                    'status': 'completed' if status == 'SUCCESS' else 'pending',
                    'transaction_id': transaction_id,
                    'provider_response': data
                }
            else:
                return {
                    'success': False,
                    'error': f"Erreur vérification: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Wave Verification Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


def get_payment_provider(payment_method, environment='production'):
    """
    Retourne le provider de paiement approprié
    
    Les clés API doivent être configurées dans settings.py ou variables d'environnement
    """
    from django.conf import settings
    
    # Récupérer les clés depuis les settings ou variables d'environnement
    # En production, utilisez des variables d'environnement sécurisées
    
    if payment_method == 'orange_money':
        api_key = getattr(settings, 'ORANGE_MONEY_API_KEY', '')
        api_secret = getattr(settings, 'ORANGE_MONEY_API_SECRET', '')
        merchant_id = getattr(settings, 'ORANGE_MONEY_MERCHANT_ID', '')
        return OrangeMoneyProvider(api_key, api_secret, merchant_id, environment)
    
    elif payment_method == 'moov_money':
        api_key = getattr(settings, 'MOOV_MONEY_API_KEY', '')
        api_secret = getattr(settings, 'MOOV_MONEY_API_SECRET', '')
        merchant_id = getattr(settings, 'MOOV_MONEY_MERCHANT_ID', '')
        return MoovMoneyProvider(api_key, api_secret, merchant_id, environment)
    
    elif payment_method == 'mtn_money':
        api_key = getattr(settings, 'MTN_MONEY_API_KEY', '')
        api_secret = getattr(settings, 'MTN_MONEY_API_SECRET', '')
        return MTNMoneyProvider(api_key, api_secret, None, environment)
    
    elif payment_method == 'wave':
        api_key = getattr(settings, 'WAVE_API_KEY', '')
        api_secret = getattr(settings, 'WAVE_API_SECRET', '')
        return WaveProvider(api_key, api_secret, None, environment)

    elif payment_method == 'paydunya':
        # Les clés sont gérées par configure_paydunya / settings/env
        # On passe des placeholders à la classe de base mais ils ne sont pas utilisés.
        return PayDunyaProvider('', '', None, environment)

    elif payment_method == 'fedapay':
        api_key = getattr(settings, 'FEDAPAY_API_KEY', '')
        api_secret = getattr(settings, 'FEDAPAY_API_SECRET', '')
        merchant_id = getattr(settings, 'FEDAPAY_MERCHANT_ID', '')
        return FedaPayProvider(api_key, api_secret, merchant_id, environment)

    elif payment_method == 'paystack':
        # Paystack se configure généralement avec une SECRET_KEY (Bearer)
        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        return PaystackProvider(secret_key, public_key, None, environment)

    elif payment_method == 'cinetpay':
        api_key = getattr(settings, 'CINETPAY_API_KEY', '')
        site_id = getattr(settings, 'CINETPAY_SITE_ID', '')
        return CinetPayProvider(api_key, settings.SECRET_KEY, site_id, environment)

    elif payment_method == 'stripe':
        secret_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        return StripeProvider(secret_key, '', None, environment)

    elif payment_method == 'paypal':
        client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
        secret = getattr(settings, 'PAYPAL_SECRET_KEY', '')
        return PayPalProvider(client_id, secret, None, environment)
    
    else:
        raise ValueError(f"Méthode de paiement non supportée: {payment_method}")

