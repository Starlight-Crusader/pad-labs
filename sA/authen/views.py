from rest_framework.views import APIView
from rest_framework.response import Response
from users.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, generics
from .serializers import UserCreateSerializer
from rest_framework.permissions import AllowAny
from sA.permissions import ProvidesValidRootPassword
from rest_framework_simplejwt.tokens import AccessToken
import time


class SignUpView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

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


class SignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        time.sleep(4)
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials."}, status=400)
        
        if not user.check_password(password):
            return Response({"detail": "Invalid credentials."}, status=400)

        refresh = RefreshToken.for_user(user)
        
        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_200_OK
        )
    

class IssueAccessTokenView(APIView):
    permission_classes = [ProvidesValidRootPassword]

    def post(self, request, user_id, *args, **kwargs):
        user_id = self.kwargs.get('user_id')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        access_token = AccessToken.for_user(user)

        return Response(
            {
                'access': str(access_token),
            },
            status=status.HTTP_200_OK
        )