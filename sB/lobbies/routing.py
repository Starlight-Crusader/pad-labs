from django.urls import path
from .consumers import LobbyConsumer


websocket_urlpatterns = [
    path('lobby/<str:lobby_identifier>', LobbyConsumer.as_asgi()),
]