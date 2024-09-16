from rest_framework import generics
from .models import User
from .serializers import UserCreateSerializer, UserListSerializer, UserSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer


class UserDestroyView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UpdateUserRatingView(APIView):
    def patch(self, request, *args, **kwargs):
        user_id = request.query_params.get('id')
        delta = request.query_params.get('delta')
        
        if not user_id or not delta:
            return Response({"error": "Both 'id' and 'delta' query parameters are required!"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found!"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            delta = int(delta)
        except ValueError:
            return Response({"error": "'delta' must be an integer!"}, status=status.HTTP_400_BAD_REQUEST)
        
        user.ratings += delta
        user.save()
        
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)