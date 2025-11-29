# Application Android pour la réception des SMS de paiement

Ce guide explique comment configurer et déployer l'application Android qui écoute les SMS de paiement et les envoie au serveur.

## Configuration requise

- Android Studio 4.0 ou supérieur
- Android 5.0 (API niveau 21) ou supérieur
- Connexion Internet
- Permissions SMS accordées

## Structure du projet

L'application contient principalement :
- `SmsReceiver` : BroadcastReceiver pour intercepter les SMS entrants
- `MainActivity` : Activité principale (peut être vide sauf pour la demande de permissions)
- `AndroidManifest.xml` : Configuration des permissions et du receiver

## Configuration

1. **Mise à jour de l'URL du serveur**
   - Dans la classe `SmsReceiver`, mettez à jour la constante `SERVER_URL` avec l'URL de votre serveur.

2. **Configuration des permissions**
   Assurez-vous que les permissions suivantes sont présentes dans `AndroidManifest.xml` :
   ```xml
   <uses-permission android:name="android.permission.RECEIVE_SMS" />
   <uses-permission android:name="android.permission.READ_SMS" />
   <uses-permission android:name="android.permission.INTERNET" />
   <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
   ```

3. **Configuration du BroadcastReceiver**
   Ajoutez ceci dans `AndroidManifest.xml` :
   ```xml
   <receiver
       android:name=".SmsReceiver"
       android:enabled="true"
       android:exported="true"
       android:permission="android.permission.BROADCAST_SMS">
       <intent-filter>
           <action android:name="android.provider.Telephony.SMS_RECEIVED" />
       </intent-filter>
   </receiver>
   ```

## Code source principal

### SmsReceiver.kt
```kotlin
package com.example.smspaymentreceiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.SmsMessage
import android.util.Log
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley

class SmsReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "SmsReceiver"
        private const val SERVER_URL = "https://votresite.com/paiements/api/sms-webhook/"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == "android.provider.Telephony.SMS_RECEIVED") {
            val bundle = intent.extras
            if (bundle != null) {
                try {
                    val pdus = bundle.get("pdus") as Array<*>
                    val messages = arrayOfNulls<SmsMessage>(pdus.size)
                    
                    for (i in pdus.indices) {
                        val pdu = pdus[i] as ByteArray
                        messages[i] = SmsMessage.createFromPdu(pdu)
                    }
                    
                    for (message in messages) {
                        message?.let { sms ->
                            val msg = sms.messageBody ?: ""
                            val sender = sms.originatingAddress ?: ""
                            
                            // Vérifier si c'est un SMS de paiement
                            if (msg.contains("FCFA", ignoreCase = true) && 
                                (msg.contains("Ref:", ignoreCase = true) || 
                                 msg.contains("REF:", ignoreCase = true))) {
                                Log.d(TAG, "SMS de paiement détecté: $msg")
                                sendToServer(context, msg, sender)
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Erreur lors du traitement du SMS: ${e.message}")
                }
            }
        }
    }
    
    private fun sendToServer(context: Context, message: String, sender: String) {
        val request = object : StringRequest(
            Request.Method.POST, SERVER_URL,
            { response ->
                Log.d(TAG, "Réponse du serveur: $response")
            },
            { error ->
                Log.e(TAG, "Erreur d'envoi au serveur: ${error.message}")
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                val params = HashMap<String, String>()
                params["message"] = message
                params["sender"] = sender
                return params
            }
            
            override fun getHeaders(): MutableMap<String, String> {
                val headers = HashMap<String, String>()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                // Vous pouvez ajouter un token d'authentification ici si nécessaire
                // headers["Authorization"] = "Token YOUR_AUTH_TOKEN"
                return headers
            }
        }
        
        // Ajouter la requête à la file d'attente
        Volley.newRequestQueue(context).add(request)
    }
}
```

### build.gradle (Module: app)
Assurez-vous d'avoir ces dépendances :
```gradle
dependencies {
    implementation 'com.android.volley:volley:1.2.1'
    // Autres dépendances...
}
```

## Tests

1. Installez l'application sur un appareil Android
2. Accordez les permissions nécessaires
3. Envoyez un SMS de test au format :
   "Vous avez reçu 5000 FCFA de +22507000000. Ref: OM12345678"
4. Vérifiez les logs pour voir si le SMS est bien reçu et envoyé au serveur

## Sécurité

1. **HTTPS** : Assurez-vous que votre serveur utilise HTTPS
2. **Authentification** : Implémentez un système d'authentification pour sécuriser l'API
3. **Validation** : Validez toujours les données reçues côté serveur
4. **Permissions** : N'utilisez que les permissions nécessaires

## Dépannage

- **Les SMS ne sont pas détectés** : Vérifiez que les permissions sont accordées dans les paramètres de l'application
- **Erreur de connexion au serveur** : Vérifiez la connexion Internet et l'URL du serveur
- **Format de message incorrect** : Vérifiez que le format du SMS correspond à celui attendu

## Prochaines étapes

1. Ajouter une interface utilisateur pour afficher l'état des envois
2. Implémenter un système de notification pour les erreurs
3. Ajouter du chiffrement pour les données sensibles
4. Mettre en place un système de journalisation local
