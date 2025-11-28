"""
Signals pour l'application payments.
"""
from django.dispatch import Signal

# Exemple de signal personnalisé (à décommenter et utiliser si nécessaire)
# payment_verified = Signal(providing_args=["instance", "created"])

# Les gestionnaires de signaux iront ici
# Par exemple :
# @receiver(post_save, sender=PaymentTransaction)
# def handle_payment_verification(sender, instance, created, **kwargs):
#     if instance.status == 'completed' and not instance.verified_at:
#         instance.verified_at = timezone.now()
#         instance.save()
