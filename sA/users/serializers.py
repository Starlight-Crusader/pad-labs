from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'rating']


class UserListSerializer(serializers.ModelSerializer):
    friends = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'rating', 'friends']

    def get_friends(self, obj):
        friends = obj.friends.all()
        return UserSerializer(friends, many=True).data