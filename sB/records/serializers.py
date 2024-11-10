from rest_framework import serializers
from .models import GameRecord
from django.utils import timezone


class GameRecordSerializer(serializers.ModelSerializer):
    finished_at = serializers.DateTimeField(default=timezone.now)

    class Meta:
        model = GameRecord
        fields = ['id', 'white_player', 'black_player', 'moves', 'finished_at']