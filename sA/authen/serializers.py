from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import User


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['username', 'password']

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])
        user.save()
        
        return user
    

class TokenValidationSerializer(serializers.Serializer):
    token = serializers.CharField()