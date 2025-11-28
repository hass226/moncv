from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import WhatsAppConfig, WhatsAppMessage

@admin.register(WhatsAppConfig)
class WhatsAppConfigAdmin(admin.ModelAdmin):
    list_display = ('default_phone_number', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    fieldsets = (
        (None, {
            'fields': ('default_phone_number', 'is_active')
        }),
        (_('Configuration API'), {
            'fields': ('api_key', 'api_url'),
            'classes': ('collapse',)
        }),
        (_('Métadonnées'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        # Ne permettre d'ajouter qu'une seule configuration
        return WhatsAppConfig.objects.count() == 0

@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ('product', 'recipient', 'status', 'created_at', 'status_updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('recipient', 'product__name', 'message')
    readonly_fields = ('created_at', 'sent_at', 'status_updated_at', 'status')
    fieldsets = (
        (None, {
            'fields': ('product', 'recipient', 'status')
        }),
        (_('Contenu du message'), {
            'fields': ('message', 'error_message')
        }),
        (_('Dates'), {
            'fields': ('created_at', 'sent_at', 'status_updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Désactiver l'ajout manuel de messages
        return False
