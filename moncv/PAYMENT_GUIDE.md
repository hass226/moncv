# 💳 Guide du Système de Paiement MYMEDAGA

## 📱 Comment fonctionne le système de paiement

### Méthodes de paiement disponibles

1. **Orange Money** : +22604647641
2. **Moov Money** : +22604647641
3. **Mobile Money** : 58485509
4. **Wave** : 58485509
5. **Carte Bancaire** : Bientôt disponible
6. **PayPal** : Bientôt disponible

## 🔄 Processus de paiement

### Pour l'utilisateur :

1. **Choisir la méthode de paiement** sur la page d'abonnement/promotion
2. **Suivre les instructions** affichées (numéro à composer, montant, etc.)
3. **Effectuer le paiement** via l'application mobile ou USSD
4. **Récupérer l'ID de transaction** reçu par SMS/notification
5. **Entrer l'ID de transaction** dans le formulaire
6. **Confirmer** - L'abonnement/promotion est activé automatiquement

### Si pas d'ID de transaction :

- La demande est mise en **attente**
- Un administrateur peut valider manuellement depuis l'admin Django
- L'utilisateur recevra une notification une fois validé

## 🛠️ Validation manuelle (Admin)

### Depuis l'interface admin Django :

1. Aller sur `/admin/stores/subscription/` ou `/admin/stores/promotion/`
2. Sélectionner les demandes en attente
3. Utiliser l'action "Approuver" pour activer automatiquement
4. Ou "Rejeter" pour annuler

## 🔧 Améliorations futures

Pour automatiser complètement le système :

1. **Intégrer les APIs de paiement** :
   - API Orange Money
   - API Moov Money
   - API Wave
   - Stripe pour les cartes bancaires
   - PayPal API

2. **Webhooks** :
   - Recevoir les notifications de paiement automatiquement
   - Valider les transactions en temps réel

3. **Vérification automatique** :
   - Vérifier l'ID de transaction avec les services de paiement
   - Activer automatiquement si valide

## 📞 Support

Pour toute question sur les paiements :
- Email : support@mymedaga.com
- WhatsApp : +22604647641

