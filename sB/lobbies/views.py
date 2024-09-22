from rest_framework import generics, status
from .models import GameLobby
from .serializers import GameLobbySerializer, CreateGameLobbySerializer
from django.db.models import Q
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.http import Http404
from sB.permissions import ProvidesValidRootPassword, ValidateTokenWithServiceA
import requests
import os


class GameLobbyListView(generics.ListAPIView):
    queryset = GameLobby.objects.all()
    serializer_class = GameLobbySerializer
    permission_classes = [ProvidesValidRootPassword]


class CreateGameLobbyView(generics.CreateAPIView):
    queryset = GameLobby.objects.all()
    serializer_class = CreateGameLobbySerializer
    permission_classes = [ValidateTokenWithServiceA]


class DiscoverGamesyLobbiesByRatingView(generics.ListAPIView):
    serializer_class = GameLobbySerializer
    permission_classes = [ValidateTokenWithServiceA]

    def get_queryset(self):
        user_rating = self.request.basic_user_info['rating']
        min_rating = user_rating - 60
        max_rating = user_rating + 60

        return GameLobby.objects.filter(
            Q(players__len__lt=2),
            rating__gte=min_rating,
            rating__lte=max_rating
        )[:3]
    

class DiscoverGamesyLobbiesWithFriendsView(generics.ListAPIView):
    serializer_class = GameLobbySerializer
    permission_classes = [ValidateTokenWithServiceA]

    def get_queryset(self):
        # Retrieve the list of friend IDs from service A
        friends_ids_response = requests.get(
            f'{os.getenv("A_BASE_URL")}api/friends/get-ids',
            headers={
                'Authorization': self.request.headers.get('Authorization'),
                'X-Root-Password': os.getenv('ROOT_PASSWORD')
            }
        )
        
        if friends_ids_response.status_code == 200:
            friends_ids = friends_ids_response.json()['friends']
        else:
            friends_ids = []

        # Filter lobbies that have friends in either the 'players' or 'spectators' arrays
        return GameLobby.objects.filter(
            Q(players__overlap=friends_ids) | Q(spectators__overlap=friends_ids)
        )[:3]
    

class ConnectToGameLobbyView(generics.UpdateAPIView):
    queryset = GameLobby.objects.all()
    serializer_class = GameLobbySerializer
    permission_classes = [ValidateTokenWithServiceA]

    def get_object(self):
        identifier = self.request.query_params.get('identifier')

        if not identifier:
            raise ValidationError({"detail": "The 'identifier' parameter is required."})

        # Fetch the lobby by the identifier
        try:
            return GameLobby.objects.get(identifier=identifier)
        except GameLobby.DoesNotExist:
            raise Http404("Lobby not found.")

    def update(self, request, *args, **kwargs):
        lobby = self.get_object()
        is_player = request.query_params.get('is_player')  # 0 for player, 1 for spectator
        user_id = request.basic_user_info['id']

        if is_player is None:
            return Response(
                {"detail": "The 'is_player' parameters is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate accepted parameter
        try:
            is_player = bool(int(is_player))
        except ValueError:
            return Response(
                {"detail": "The 'is_player' parameter must be '1' or '0'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user_id in lobby.players + lobby.spectators:
            return Response(
                {"detail": "You are already in this lobby."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if is_player:  # Connect as the second player
            if len(lobby.players) < 2:
                if user_id not in lobby.players:
                    lobby.players.append(user_id)
                else:
                    return Response(
                        {'detail': 'User is already a player in this lobby.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {'detail': 'Lobby already has 2 players.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:  # Connect as a spectator
            if user_id not in lobby.spectators:
                lobby.spectators.append(user_id)

        lobby.save()
        return Response(self.get_serializer(lobby).data)
    

class GameLobbyDestroyView(generics.DestroyAPIView):
    queryset = GameLobby.objects.all()
    serializer_class = GameLobbySerializer
    permission_classes = [ProvidesValidRootPassword]

    def delete(self, request, *args, **kwargs):
        super().delete(request, *args, **kwargs)

        return Response(
            {'detail': "Lobby removed successfully."},
            status=status.HTTP_200_OK
        )