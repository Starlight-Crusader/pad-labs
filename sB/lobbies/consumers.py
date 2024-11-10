import os
import requests
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework.exceptions import PermissionDenied
from channels.db import database_sync_to_async
from django.core.cache import cache
from sB.utilities import get_timeout_from_token
import asyncio


class LobbyConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()

        self.lobby_identifier = self.scope['url_route']['kwargs']['lobby_identifier']
        self.room_group_name = f'lobby_{self.lobby_identifier}'

        # Extract the authorization header from the WebSocket request
        token = self.get_token_from_headers(self.scope['headers'])

        if token is None:
            await self.send_error("No auth. credentials provided.")
            await self.close()
            return

        # Validate the JWT token
        if not await self.validate_token_and_fetch_user_data(token):
            await self.send_error("Invalid auth. credentials.")
            await self.close()
            return

        self.user_id = self.scope['user_data']['id']

        # Check if connecting user is registered to be in the lobby
        if not (await self.is_player_in_lobby(self.user_id) or await self.is_spectator_in_lobby(self.user_id)):
            self.user_id = None
            await self.send_error("This is an unauthorized access attempt.")
            await self.close()
            return

        # Join lobby group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': f'{self.scope['user_data']['username']} has joined the lobby.'
            }
        )

    async def disconnect(self, close_code):
        if self.user_id:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': f'{self.scope['user_data']['username']} has disconnected.'
                }
            )

            user_id = self.scope['user_data']['id']

            # Leave lobby group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            # Remove user from the lobby
            await self.remove_user_from_lobby(user_id)

    async def receive_json(self, content, **kwargs):
        type = content.get('type', '')
        message = content.get('message', '')

        # Check if the user is a player in the lobby
        if await self.is_spectator_in_lobby(self.user_id) and type == 'move_message':
            await self.send_error("Only players can issue moves.")
            return

        # Send message to lobby group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': type,
                'message': f"{self.scope['user_data']['username']}: {message}"
            }
        )

    async def chat_message(self, event):
        type = event['type']
        message = event['message']

        # Send message to WebSocket
        await self.send_json({
            'type': type,
            'message': message
        })

    async def move_message(self, event):
        type = event['type']
        message = event['message']

        # Send message to WebSocket
        await self.send_json({
            'type': type,
            'message': message
        })

    async def validate_token_and_fetch_user_data(self, full_token_str):
        token = full_token_str.split(' ')[1]

        cached_user_data = cache.get(token + "_user_data")
        if cached_user_data:
            print(f"Using cached data for user #{cached_user_data.get('id')}")
            self.scope['user_data'] = cached_user_data
            return True

        try:
            response = requests.get(f'{os.getenv("API_GATEWAY_BASE_URL")}sA/api/utilities/validate-token', headers={
                'Authorization': full_token_str,
                'X-Root-Password': os.getenv('ROOT_PASSWORD')
            })
            
            if response.status_code == 200:
                user_data = response.json()
                self.scope['user_data'] = user_data
                self.cache_user_data(token, user_data)
                return True
        except requests.RequestException:
            return False
        
        return False
    
    def cache_user_data(self, token, user_data):
        timeout = get_timeout_from_token(token)

        if timeout is not None:
            cache.set(token + "_user_data", user_data, timeout=timeout)
            print(f"Cached data for user #{user_data.get('id')}")
    
    async def is_player_in_lobby(self, user_id):
        from lobbies.models import GameLobby

        try:
            lobby = await database_sync_to_async(GameLobby.objects.get)(identifier=self.lobby_identifier)
            return user_id in lobby.players
        except GameLobby.DoesNotExist:
            return False
        
    async def is_spectator_in_lobby(self, user_id):
        from lobbies.models import GameLobby

        try:
            lobby = await database_sync_to_async(GameLobby.objects.get)(identifier=self.lobby_identifier)
            return user_id in lobby.spectators 
        except GameLobby.DoesNotExist:
            return False
    
    async def remove_user_from_lobby(self, user_id):
        from lobbies.models import GameLobby

        try:
            lobby = await database_sync_to_async(GameLobby.objects.get)(identifier=self.lobby_identifier)

            # Check if user is in players or spectators and remove them
            if user_id in lobby.players:
                lobby.players.remove(user_id)
            elif user_id in lobby.spectators:
                lobby.spectators.remove(user_id)

            await database_sync_to_async(lobby.save)()

            # If the lobby is empty - destroy it
            if not lobby.players and not lobby.spectators:
                await database_sync_to_async(lobby.delete)()

        except GameLobby.DoesNotExist:
            # Handle case where the lobby does not exist
            pass

    async def send_error(self, error_message):
        await self.send_json({
            'type': 'error',
            'detail': error_message
        })

    def get_token_from_headers(self, headers):
        for key, value in headers:
            if key == b'authorization':
                return value.decode('utf-8')  # Decode from bytes to string
        return None