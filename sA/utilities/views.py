from rest_framework.views import APIView
from sA.permissions import ProvidesValidRootPassword
from rest_framework.permissions import IsAuthenticated
from users.models import User
from rest_framework.response import Response
from rest_framework import status
from users.serializers import UserSerializer
import time
import os


class ValidateTokenForBView(APIView):
    permission_classes = [ProvidesValidRootPassword, IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        user = User.objects.get(id=user_id)

        basic_user_info = UserSerializer(user).data
        return Response(basic_user_info, status=status.HTTP_200_OK)
    

class StatusView(APIView):
    permission_classes = [ProvidesValidRootPassword]

    def get(self, request):
        return Response(
            {'message': f"Instance of service A running on 127.0.0.1:{os.getenv('PORT')} is alive!"},
            status=status.HTTP_202_ACCEPTED
        )
    

class SleepyView(APIView):
    permission_classes = [ProvidesValidRootPassword]

    def get(self, request):
        time.sleep(int(os.getenv('SLEEP_DURATION_S')))

        return Response(
            {'message': f"You are not supposed to see this message!"},
            status=status.HTTP_202_ACCEPTED
        )
