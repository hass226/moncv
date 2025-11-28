from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

# Importer les vues directement depuis leurs modules
from .views.views import (
    process_payment, payment_instructions, payment_confirm,
    verify_payment, payment_status, payment_success, payment_cancel,
    stripe_webhook, my_transactions, generate_verification_codes,
    view_generated_codes, verify_payment_code, delete_code, CodeDashboard, 
    export_codes, mark_code_used, PromoteView
)
from .views import whatsapp_views
from .views.whatsapp_order import process_whatsapp_order, whatsapp_webhook

# Importer les autres modules nécessaires
from .webhooks import sms_webhook
from .api_views import sms_webhook, get_payment_status, create_mobile_money_payment

app_name = 'payments'

urlpatterns = [
    # URLs pour les utilisateurs
    path('paiement/<int:plan_id>/', login_required(process_payment), name='process_payment'),
    path('paiement/', login_required(process_payment), name='process_payment_without_plan'),
    path('paiement/confirmation/<str:transaction_id>/', login_required(payment_confirm), name='payment_confirm'),
    path('instructions/', login_required(payment_instructions), name='payment_instructions'),
    path('verifier-paiement/', verify_payment, name='verify_payment'),
    path('verifier-code/', login_required(verify_payment_code), name='verify_payment_code'),
    path('statut-paiement/<str:transaction_id>/', payment_status, name='payment_status'),
    path('mes-transactions/', login_required(my_transactions), name='my_transactions'),
    
    # URLs pour les retours de paiement
    path('payment/success/', payment_success, name='payment_success'),
    path('payment/cancel/', payment_cancel, name='payment_cancel'),
    
    # Webhooks
    path('webhook/stripe/', stripe_webhook, name='stripe_webhook'),
    
    # URL pour la promotion
    path('promote/', PromoteView.as_view(), name='promote'),
    
    # URLs pour les messages WhatsApp
    path('whatsapp/send/<int:product_id>/', 
         login_required(whatsapp_views.send_whatsapp_message), 
         name='send_whatsapp_message'),
    path('whatsapp/send-ajax/<int:product_id>/', 
         login_required(whatsapp_views.send_whatsapp_ajax), 
         name='send_whatsapp_ajax'),
    path('whatsapp/order/<int:product_id>/', 
         login_required(process_whatsapp_order), 
         name='whatsapp_order'),
    path('whatsapp/webhook/', 
         whatsapp_webhook, 
         name='whatsapp_webhook'),
    path('whatsapp/messages/', 
         login_required(whatsapp_views.whatsapp_message_list), 
         name='whatsapp_message_list'),
    path('whatsapp/messages/<int:message_id>/', 
         login_required(whatsapp_views.whatsapp_message_detail), 
         name='whatsapp_message_detail'),
    
    # Gestion des codes de vérification
    path(
        'codes/', 
        login_required(CodeDashboard.as_view()),
        name='code_dashboard'
    ),
    
    # Génération de codes de vérification
    path(
        'codes/generate/', 
        login_required(generate_verification_codes), 
        name='generate_verification_codes'
    ),
    
    # Affichage des codes générés
    path(
        'codes/view/', 
        login_required(view_generated_codes), 
        name='view_generated_codes'
    ),
    
    # Exportation des codes
    path(
        'codes/export/',
        login_required(export_codes),
        name='export_codes'
    ),
    
    # Marquer un code comme utilisé (API)
    path(
        'codes/<int:code_id>/mark-used/', 
        login_required(mark_code_used), 
        name='mark_code_used'
    ),
    
    # ====================================================
    # API Endpoints
    # ====================================================
    
    # Webhook pour Mobile Money
    path('api/mobile-money/webhook/', sms_webhook, name='mobile_money_webhook'),
    
    # Statut des paiements
    path(
        'api/mobile-money/status/<str:transaction_id>/', 
        get_payment_status, 
        name='payment_status_api'
    ),
    
    # Création d'un paiement Mobile Money
    path(
        'api/mobile-money/pay/', 
        create_mobile_money_payment, 
        name='create_mobile_money_payment'
    ),
    
    # Webhook pour la réception des SMS de paiement
    path('api/sms-webhook/', sms_webhook, name='sms_webhook'),
    
    # Suppression d'un code de vérification
    path(
        'codes/<int:code_id>/delete/', 
        login_required(delete_code), 
        name='delete_code'
    ),
]
