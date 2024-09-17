from rest_framework import serializers
from .models import FriendRequest


class FriendRequestListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = FriendRequest
        fields = ['id', 'sender', 'receiver', 'status']


class ReceivedFriendRequestListSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = FriendRequest
        fields = ['id', 'sender']