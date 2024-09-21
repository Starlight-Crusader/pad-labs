from django.urls import path
from .views import GameLobbyListView, GameLobbyDestroyView, CreateGameLobbyView, DiscoverGameLobbiesView, ConnectToGameLobbyView


urlpatterns = [
    path('list/',GameLobbyListView.as_view(), name='gl-list'),
    path('<int:pk>/destroy/', GameLobbyDestroyView.as_view(), name='gl-destroy'),
    path('create/', CreateGameLobbyView.as_view(), name='gl-create'),
    path('discover/', DiscoverGameLobbiesView.as_view(), name='dl-discover'),
    path('connect/', ConnectToGameLobbyView.as_view(), name='dl-connect')
]