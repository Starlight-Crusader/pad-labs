from rest_framework.views import APIView
from sB.permissions import ProvidesValidRootPassword
from rest_framework.response import Response
from rest_framework import status
import os


class StatusView(APIView):
    permission_classes = [ProvidesValidRootPassword]

    def get(self, request):
        return Response(
            {'message': f"Instance of service B running on 127.0.0.1:{os.getenv('PORT')} is alive!"},
            status=status.HTTP_202_ACCEPTED
        )