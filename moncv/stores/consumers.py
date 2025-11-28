"""
WebSocket consumers pour Live Commerce
"""

import json

try:
    from channels.generic.websocket import AsyncWebsocketConsumer
    from channels.db import database_sync_to_async
    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False
    # Créer des classes factices si channels n'est pas disponible
    class AsyncWebsocketConsumer:
        pass
    def database_sync_to_async(func):
        return func

from django.contrib.auth.models import User
from .models import LiveStream, LiveComment, LiveProduct


class LiveStreamConsumer(AsyncWebsocketConsumer):
    """Consumer pour les streams live"""
    
    async def connect(self):
        self.live_id = self.scope['url_route']['kwargs']['live_id']
        self.room_group_name = f'live_{self.live_id}'
        
        # Rejoindre le groupe
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Mettre à jour le nombre de viewers
        await self.update_viewers_count(1)
    
    async def disconnect(self, close_code):
        # Quitter le groupe
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Mettre à jour le nombre de viewers
        await self.update_viewers_count(-1)
    
    async def receive(self, text_data):
        """Recevoir un message du client"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'comment':
            # Nouveau commentaire
            comment = await self.create_comment(data)
            if comment:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'comment_message',
                        'comment': comment
                    }
                )
        
        elif message_type == 'viewer_count':
            # Mise à jour du nombre de viewers
            count = await self.get_viewers_count()
            await self.send(text_data=json.dumps({
                'type': 'viewer_count',
                'count': count
            }))
    
    async def comment_message(self, event):
        """Envoyer un commentaire au client"""
        await self.send(text_data=json.dumps({
            'type': 'comment',
            'comment': event['comment']
        }))
    
    async def product_update(self, event):
        """Mise à jour d'un produit"""
        await self.send(text_data=json.dumps({
            'type': 'product_update',
            'product': event['product']
        }))
    
    async def purchase_notification(self, event):
        """Notification d'achat"""
        await self.send(text_data=json.dumps({
            'type': 'purchase',
            'purchase': event['purchase']
        }))
    
    @database_sync_to_async
    def create_comment(self, data):
        """Créer un commentaire"""
        try:
            live_stream = LiveStream.objects.get(id=self.live_id)
            user = User.objects.get(id=data.get('user_id'))
            
            comment = LiveComment.objects.create(
                live_stream=live_stream,
                user=user,
                content=data.get('content', ''),
                is_question=data.get('is_question', False)
            )
            
            return {
                'id': comment.id,
                'user': user.username,
                'content': comment.content,
                'is_question': comment.is_question,
                'created_at': comment.created_at.isoformat()
            }
        except Exception as e:
            return None
    
    @database_sync_to_async
    def update_viewers_count(self, delta):
        """Mettre à jour le nombre de viewers"""
        try:
            live_stream = LiveStream.objects.get(id=self.live_id)
            live_stream.viewers_count = max(0, live_stream.viewers_count + delta)
            if live_stream.viewers_count > live_stream.peak_viewers:
                live_stream.peak_viewers = live_stream.viewers_count
            live_stream.save()
        except:
            pass
    
    @database_sync_to_async
    def get_viewers_count(self):
        """Obtenir le nombre de viewers"""
        try:
            live_stream = LiveStream.objects.get(id=self.live_id)
            return live_stream.viewers_count
        except:
            return 0

