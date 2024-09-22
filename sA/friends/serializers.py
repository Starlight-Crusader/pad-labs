from rest_framework import serializers
from .models import FriendRequest
from users.models import User


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


class FriendsIdsListSerializer(serializers.ModelSerializer):
    friends = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['friends']