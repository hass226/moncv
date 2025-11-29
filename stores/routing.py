"""
WebSocket routing pour Live Commerce
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/live/(?P<live_id>\w+)/$', consumers.LiveStreamConsumer.as_asgi()),
]

