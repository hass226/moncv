import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    PaymentTransaction, 
    SubscriptionPlan, 
    StoreSubscription, 
    PaymentVerificationCode
)
from .mobile_money import MobileMoneyConfig

class ExportCsvMixin:
    """Mixin to add export as CSV action"""
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}.csv'
        
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response
    
    export_as_csv.short_description = _("Export Selected as CSV")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        (_('Pricing'), {
            'fields': ('price', 'duration_days')
        }),
        (_('Features'), {
            'fields': ('features',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class StoreSubscriptionInline(admin.StackedInline):
    model = StoreSubscription
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('plan', 'status', 'start_date', 'end_date', 'created_at')
    show_change_link = True


@admin.register(StoreSubscription)
class StoreSubscriptionAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('store', 'plan', 'status', 'start_date', 'end_date', 'is_active')
    list_filter = ('status', 'plan')
    search_fields = ('store__name', 'store__owner__username')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('store', 'plan')
    actions = ['export_as_csv', 'extend_subscription']
    
    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True
    is_active.short_description = _('Active')
    
    def extend_subscription(self, request, queryset):
        days = request.POST.get('days', 30)
        try:
            days = int(days)
            count = 0
            for subscription in queryset:
                if subscription.end_date:
                    subscription.end_date += timezone.timedelta(days=days)
                else:
                    subscription.start_date = timezone.now()
                    subscription.end_date = timezone.now() + timezone.timedelta(days=days)
                subscription.save()
                count += 1
            self.message_user(
                request, 
                _('Successfully extended %(count)d subscriptions by %(days)d days.') % {
                    'count': count,
                    'days': days
                },
                messages.SUCCESS
            )
        except ValueError:
            self.message_user(request, _('Invalid number of days'), messages.ERROR)
    extend_subscription.short_description = _('Extend selected subscriptions by X days')


@admin.register(PaymentVerificationCode)
class PaymentVerificationCodeAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('code', 'subscription_info', 'status', 'created_by', 'created_at', 'expires_at', 'is_valid')
    list_filter = ('status', 'subscription__plan')
    search_fields = ('code', 'subscription__store__name', 'subscription__plan__name')
    readonly_fields = ('created_at', 'used_at', 'expires_at', 'is_valid')
    list_select_related = ('subscription', 'subscription__plan', 'subscription__store', 'created_by')
    actions = ['export_as_csv', 'generate_codes', 'mark_as_used', 'mark_as_expired']
    
    def subscription_info(self, obj):
        return f"{obj.subscription.store.name} - {obj.subscription.plan.name}"
    subscription_info.short_description = _('Subscription')
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = _('Is Valid')
    
    def generate_codes(self, request, queryset):
        """Generate new verification codes for selected subscriptions"""
        count = int(request.POST.get('count', 1))
        days_valid = int(request.POST.get('days_valid', 7))
        
        if count <= 0 or days_valid <= 0:
            self.message_user(request, _('Count and days must be positive numbers'), messages.ERROR)
            return
            
        created = 0
        for subscription in queryset:
            for _ in range(count):
                code = PaymentVerificationCode.objects.create(
                    subscription=subscription,
                    created_by=request.user,
                    expires_at=timezone.now() + timezone.timedelta(days=days_valid)
                )
                created += 1
                
        self.message_user(
            request, 
            _('Successfully created %(count)d verification codes for %(subs)d subscriptions.') % {
                'count': created,
                'subs': queryset.count()
            },
            messages.SUCCESS
        )
    generate_codes.short_description = _('Generate verification codes')
    
    def mark_as_used(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='used',
            used_by=request.user,
            used_at=timezone.now()
        )
        self.message_user(
            request,
            _('Successfully marked %(count)d codes as used.') % {'count': updated},
            messages.SUCCESS
        )
    mark_as_used.short_description = _('Mark selected codes as used')
    
    def mark_as_expired(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='expired',
            expires_at=timezone.now()
        )
        self.message_user(
            request,
            _('Successfully expired %(count)d codes.') % {'count': updated},
            messages.SUCCESS
        )
    mark_as_expired.short_description = _('Mark selected codes as expired')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('transaction_id', 'user', 'payment_method', 'amount', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'service_type')
    search_fields = ('transaction_id', 'user__username', 'phone_number')
    readonly_fields = ('created_at', 'verified_at')
    actions = ['export_as_csv', 'mark_as_completed', 'mark_as_failed']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='completed',
            verified_at=timezone.now()
        )
        self.message_user(
            request,
            _('Successfully marked %(count)d transactions as completed.') % {'count': updated},
            messages.SUCCESS
        )
    mark_as_completed.short_description = _('Mark selected transactions as completed')
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='failed')
        self.message_user(
            request,
            _('Successfully marked %(count)d transactions as failed.') % {'count': updated},
            messages.SUCCESS
        )
    mark_as_failed.short_description = _('Mark selected transactions as failed')
    date_hierarchy = 'created_at'

@admin.register(MobileMoneyConfig)
class MobileMoneyConfigAdmin(admin.ModelAdmin):
    list_display = ('operator', 'sms_sender', 'is_active')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
