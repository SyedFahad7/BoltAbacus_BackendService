from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/pvp/(?P<room_id>\w+)/$', consumers.PVPConsumer.as_asgi()),
]
