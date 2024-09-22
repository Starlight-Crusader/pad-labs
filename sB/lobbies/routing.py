from django.urls import path
from .consumers import LobbyConsumer


websocket_urlpatterns = [
    path('lobby/<str:lobby_id>', LobbyConsumer.as_asgi()),
]