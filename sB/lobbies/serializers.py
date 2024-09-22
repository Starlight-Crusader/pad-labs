from rest_framework import serializers
from .models import GameLobby


class GameLobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = GameLobby
        fields = ['id', 'identifier', 'players', 'spectators', 'rating']


class CreateGameLobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = GameLobby
        fields = ['identifier', 'players', 'rating']

    def create(self, validated_data):
        user_id = self.context['request'].basic_user_info['id']
        user_rating = round(self.context['request'].basic_user_info['rating'])

        validated_data['players'] = [user_id]
        validated_data['rating'] = user_rating

        print(validated_data)
        
        return super().create(validated_data)