from rest_framework import generics, status
from .models import GameLobby
from .serializers import GameLobbySerializer, CreateGameLobbySerializer, GameLobbyListSerialzer, ConnectToGameLobbySerializer
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from sB.permissions import ProvidesValidRootPassword, ValidateTokenWithServiceA
import requests
import os
from django.core.cache import cache
from sB.utilities import get_timeout_from_token
from rest_framework.exceptions import APIException


def get_new_access_token(user_id):
    try:
        service_a_url = f"{os.getenv('API_GATEWAY_BASE_URL')}sA/api/authen/token/{user_id}"
        headers = {
            'X-Root-Password': os.getenv('ROOT_PASSWORD')
        }

        response = requests.get(service_a_url, headers=headers)

        if response.status_code == 200:
            return response.json().get('access')
        else:
            raise APIException(f"Failed to get a new token from A: {response.status_code}, {response.text}")
    
    except requests.RequestException as e:
        raise APIException(f"Error communicating with Service A: {str(e)}")


class GameLobbyListView(generics.ListAPIView):
    queryset = GameLobby.objects.all()
    serializer_class = GameLobbySerializer
    permission_classes = [ProvidesValidRootPassword]


class CreateGameLobbyView(generics.CreateAPIView):
    queryset = GameLobby.objects.all()
    serializer_class = CreateGameLobbySerializer
    permission_classes = [ValidateTokenWithServiceA]

    def create(self, request, *args, **kwargs):
        # Call the superclass's create method to create the game lobby
        response = super().create(request, *args, **kwargs)

        user_id = request.basic_user_info['id']
        access = get_new_access_token(user_id)

        if not access:
            return Response(
                {'detail': 'Failed to issue access token.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                'lobby': response.data,
                'access': access
            },
            status=status.HTTP_201_CREATED
        )


class DiscoverGamesyLobbiesByRatingView(generics.ListAPIView):
    serializer_class = GameLobbyListSerialzer
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
    serializer_class = GameLobbyListSerialzer
    permission_classes = [ValidateTokenWithServiceA]

    def get_queryset(self):
        token = self.request.headers.get('Authorization')

        cached_friends_ids = cache.get(token + "_friends_ids")
        if cached_friends_ids is not None:
            print("Using cached friends IDs")
            friends_ids = cached_friends_ids
        else:
            # Retrieve the list of friend IDs from service A
            friends_ids_response = requests.get(
                f'{os.getenv("A_BASE_URL")}api/friends/get-ids',
                headers={
                    'Authorization': token,
                    'X-Root-Password': os.getenv('ROOT_PASSWORD')
                }
            )
            
            if friends_ids_response.status_code == 200:
                friends_ids = friends_ids_response.json().get('friends', [])
                
                # Cache the friend IDs with the appropriate timeout
                timeout = get_timeout_from_token(token)  # Use the timeout function
                if timeout is not None:
                    cache.set(token + "_friends_ids", friends_ids, timeout=timeout)
                    print("Cached friends IDs")

            else:
                friends_ids = []

        # Filter lobbies that have friends in either the 'players' or 'spectators' arrays
        return GameLobby.objects.filter(
            Q(players__overlap=friends_ids) | Q(spectators__overlap=friends_ids)
        )[:3]
    

class ConnectToGameLobbyView(generics.UpdateAPIView):
    queryset = GameLobby.objects.all()
    serializer_class = ConnectToGameLobbySerializer
    permission_classes = [ValidateTokenWithServiceA]

    def get_object(self):
        gl_id = self.request.query_params.get('id')

        if not gl_id:
            raise ValidationError({"detail": "The 'id' parameter is required."})

        try:
            return GameLobby.objects.get(id=gl_id)
        except GameLobby.DoesNotExist:
            raise NotFound("Lobby not found.")

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

        access = get_new_access_token(user_id)

        if not access:
            return Response(
                {'detail': 'Failed to issue a new access.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        lobby.save()
        return Response(
            {
                'lobby': self.get_serializer(lobby).data,
                'access': access
            },
            status=status.HTTP_200_OK
        )
    

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