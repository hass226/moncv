from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from .models import PaymentVerificationCode

@shared_task
def clean_expired_codes():
    """
    Tâche planifiée pour marquer les codes expirés comme 'expired'
    """
    expired = PaymentVerificationCode.objects.filter(
        Q(status='pending') & 
        Q(expires_at__lte=timezone.now())
    )
    count = expired.update(status='expired')
    return f"{count} codes marqués comme expirés"

@shared_task
def get_code_statistics():
    """
    Récupère les statistiques d'utilisation des codes
    """
    from django.db.models import Count, Case, When, IntegerField
    
    stats = {
        'total': PaymentVerificationCode.objects.count(),
        'used': PaymentVerificationCode.objects.filter(status='used').count(),
        'pending': PaymentVerificationCode.objects.filter(status='pending').count(),
        'expired': PaymentVerificationCode.objects.filter(status='expired').count(),
    }
    
    # Statistiques par statut et par boutique
    by_status = (PaymentVerificationCode.objects
               .values('status')
               .annotate(count=Count('id'))
               .order_by('-count'))
               
    by_store = (PaymentVerificationCode.objects
              .values('subscription__store__name')
              .annotate(
                  total=Count('id'),
                  used=Count(Case(When(status='used', then=1), output_field=IntegerField())),
                  pending=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
                  expired=Count(Case(When(status='expired', then=1), output_field=IntegerField()))
              )
              .order_by('-total'))
    
    stats['by_status'] = list(by_status)
    stats['by_store'] = list(by_store)
    
    return stats
