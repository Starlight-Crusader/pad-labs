from rest_framework.views import APIView
from sB.permissions import ProvidesValidRootPassword
from rest_framework.response import Response
from rest_framework import status


class StatusView(APIView):
    permission_classes = [ProvidesValidRootPassword]

    def get(self, request):
        return Response(
            {'message': f"Instance of service B running on {request.get_host()} is fine!"},
            status=status.HTTP_202_ACCEPTED
        )