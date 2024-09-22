from rest_framework.views import APIView
from rest_framework.response import Response
from users.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, generics
from .serializers import UserCreateSerializer
from rest_framework.permissions import AllowAny
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import os


class SignUpView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    timeout_seconds = int(os.getenv('VIEW_LEVEL_TIMEOUT_S'))

    def create_user(self, request):
        # Call the default create method to handle user creation
        return super().create(request)

    def post(self, request, *args, **kwargs):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.create_user, request)

        try:
            response = future.result(timeout=self.timeout_seconds)

            return Response(
                {
                    'detail': 'Account created successfully.',
                    'user': response.data
                },
                status=status.HTTP_201_CREATED
            )
        except TimeoutError:
            return Response(
                {"detail": "Request timeout, please try again."},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )


class SignInView(APIView):
    permission_classes = [AllowAny]
    timeout_seconds = int(os.getenv('VIEW_LEVEL_TIMEOUT_S'))

    def authenticate_user(self, username, password):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return {"error": "Invalid credentials."}, None

        if not user.check_password(password):
            return {"error": "Invalid credentials."}, None
        
        return None, user

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.authenticate_user, username, password)

        try:
            error, user = future.result(timeout=self.timeout_seconds)

            if error:
                return Response(
                    {"detail": error},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate tokens for the user
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                status=status.HTTP_200_OK
            )
        except TimeoutError:
            return Response(
                {"detail": "Request timeout, please try again."},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )