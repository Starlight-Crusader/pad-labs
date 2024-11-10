from rest_framework import serializers
from .models import GameLobby


class GameLobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = GameLobby
        fields = ['id', 'identifier', 'players', 'spectators', 'rating']


class GameLobbyListSerialzer(serializers.ModelSerializer):
    class Meta:
        model = GameLobby
        fields = ['id', 'players', 'spectators', 'rating']


class ConnectToGameLobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = GameLobby
        fields = ['connect_url']


class CreateGameLobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = GameLobby
        fields = ['connect_url']

    def create(self, validated_data):
        user_id = self.context['request'].user_data['id']
        user_rating = round(self.context['request'].user_data['rating'])

        validated_data['players'] = [user_id]
        validated_data['rating'] = user_rating
        
        return super().create(validated_data)