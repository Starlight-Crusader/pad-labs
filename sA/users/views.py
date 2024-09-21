from rest_framework import generics
from .models import User
from .serializers import UserListSerializer, UserSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sA.permissions import ProvidesValidRootPassword


class UserListView(generics.ListAPIView):
    serializer_class = UserListSerializer
    permission_classes = [ProvidesValidRootPassword]

    def get_queryset(self):
        user_id = self.request.query_params.get('id', None)
        if user_id:
            return User.objects.filter(id=user_id)
        return User.objects.all()


class UserDestroyView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [ProvidesValidRootPassword]

    def delete(self, request, *args, **kwargs):
        super().delete(request, *args, **kwargs)

        return Response(
            {'detail': "Account removed successfully."},
            status=status.HTTP_200_OK
        )


class UserUpdateRatingView(APIView):
    permission_classes = [ProvidesValidRootPassword]

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
        
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)