from rest_framework.views import APIView
from rest_framework.response import Response
from users.models import User
from users.serializers import BasicUserDataSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, generics
from .serializers import UserCreateSerializer
from rest_framework.permissions import AllowAny
from sA.permissions import ProvidesValidRootPassword
from .serializers import TokenValidationSerializer
from rest_framework.permissions import IsAuthenticated


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


class ValidateTokenForBView(APIView):
    permission_classes = [ProvidesValidRootPassword, IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        user = User.objects.get(id=user_id)

        basic_user_info = BasicUserDataSerializer(user).data
        return Response(basic_user_info, status=status.HTTP_200_OK)