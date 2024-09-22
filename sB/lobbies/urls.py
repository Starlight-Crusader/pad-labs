from django.urls import path
from .views import GameLobbyListView, GameLobbyDestroyView, CreateGameLobbyView, DiscoverGamesyLobbiesByRatingView, ConnectToGameLobbyView, DiscoverGamesyLobbiesWithFriendsView


urlpatterns = [
    path('list/',GameLobbyListView.as_view(), name='gl-list'),
    path('<int:pk>/destroy/', GameLobbyDestroyView.as_view(), name='gl-destroy'),
    path('create/', CreateGameLobbyView.as_view(), name='gl-create'),
    path('discover/rating/', DiscoverGamesyLobbiesByRatingView.as_view(), name='dl-discover-rating'),
    path('discover/friends/', DiscoverGamesyLobbiesWithFriendsView.as_view(), name='dl-discover-friends'),
    path('connect/', ConnectToGameLobbyView.as_view(), name='dl-connect')
]