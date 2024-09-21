from rest_framework import serializers
from .models import GameRecord


class GameRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameRecord
        fields = ['id', 'white_player', 'black_player', 'moves', 'finished_at']

    def create(self, validated_data):
        return super().create(validated_data)