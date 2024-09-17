from rest_framework import generics
from .models import User
from .serializers import UserCreateSerializer, UserListSerializer, UserSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
import os


class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer

    def post(self, request, *args, **kwargs):
        # Call the default create method to handle user creation
        response = super().create(request, *args, **kwargs)

        # Customize the response with a confirmation message
        return Response(
            {
                'detail': 'Account created successfully.',
                'user': response.data
            },
            status=status.HTTP_201_CREATED
        )


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDestroyView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer

    def delete(self, request, *args, **kwargs):
        password = request.headers.get('X-Root-Password')
        
        # Check if password is provided
        if not password:
            return Response({"detail": "Authorization credentials are missing."}, status=status.HTTP_403_FORBIDDEN)

        # Verify the password
        if password != os.getenv('ROOT_PASSWORD'):
            return Response({"detail": "Authorization credentials are invalid."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed with the destruction of the instance
        super().delete(request, *args, **kwargs)

        return Response(
            {'detail': "Account removed successfully."},
            status=status.HTTP_200_OK
        )


class UserUpdateRatingView(APIView):
    def patch(self, request, *args, **kwargs):
        user_id = request.query_params.get('id')
        delta = request.query_params.get('delta')
        
        if not user_id or not delta:
            return Response({"detail": "Both 'id' and 'delta' query parameters are required!"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found!"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            delta = int(delta)
        except ValueError:
            return Response({"detail": "'delta' must be an integer!"}, status=status.HTTP_400_BAD_REQUEST)
        
        user.rating += delta
        user.save()
        
        serializer = UserListSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)