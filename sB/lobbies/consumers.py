import os
import requests
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework.exceptions import PermissionDenied
from channels.db import database_sync_to_async


class LobbyConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.lobby_identifier = self.scope['url_route']['kwargs']['identifier']
        self.room_group_name = f'lobby_{self.lobby_identifier}'

        # Extract the authorization header from the WebSocket request
        token = self.scope['headers'].get('authorization', [None])[0]

        # Validate the JWT token
        if not await self.validate_token(token):
            raise PermissionDenied("Invalid token")
        
        # Check if connecting user is registered to be in the lobby
        user_id = self.scope['basic_user_info']['id']
        if not await self.is_user_in_lobby(user_id):
            raise PermissionDenied("This is an unauthorized access attempt")

        # Join lobby group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        user_id = self.scope['basic_user_info']['id']

        # Leave lobby group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Remove user from the lobby
        await self.remove_user_from_lobby(user_id)

    async def receive_json(self, content, **kwargs):
        message = content.get('message', '')

        # Send message to lobby group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'lobby_message',
                'message': message
            }
        )

    async def lobby_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send_json({
            'message': message
        })

    async def validate_token(self, token):
        try:
            response = requests.get(f'{os.getenv("A_BASE_URL")}api/utilities/validate-token', headers={
                'Authorization': token,
                'X-Root-Password': os.getenv('ROOT_PASSWORD')
            })
            
            if response.status_code == 200:
                self.scope['basic_user_info'] = response.json()
                return True
        except requests.RequestException:
            return False
        
        return False
    
    async def is_user_in_lobby(self, user_id):
        from lobbies.models import GameLobby

        try:
            lobby = await database_sync_to_async(GameLobby.objects.get)(identifier=self.lobby_identifier)
            return user_id in lobby.players or user_id in lobby.spectators
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