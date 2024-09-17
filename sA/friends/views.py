from rest_framework import generics, status, views
from users.models import User
from users.serializers import UserListSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import FriendRequest
from users.models import User
import os
from .serializers import FriendRequestListSerializer, ReceivedFriendRequestListSerializer


class UserSearchView(generics.ListAPIView):
    serializer_class = UserListSerializer

    def get_queryset(self):
        username_part = self.request.query_params.get('name', '')
        return User.objects.filter(username__icontains=username_part)
    

class FriendRequestListView(generics.ListAPIView):
    queryset = FriendRequest.objects.all()
    serializer_class = FriendRequestListSerializer

    def list(self, request, *args, **kwargs):
        password = request.headers.get('X-Root-Password')
        
        # Check if password is provided
        if not password:
            return Response({"detail": "Authorization credentials are missing."}, status=status.HTTP_403_FORBIDDEN)

        # Verify the password
        if password != os.getenv('ROOT_PASSWORD'):
            return Response({"detail": "Authorization credentials are invalid."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed with listing the users
        return super().list(request, *args, **kwargs)
    

class ReceivedFriendRequestsListView(generics.ListAPIView):
    serializer_class = ReceivedFriendRequestListSerializer

    def get_queryset(self):
        receiver_id = self.request.query_params.get('receiver_id')

        try:
            user = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return FriendRequest.objects.none()
        
        PENDING = 0
        
        return FriendRequest.objects.filter(receiver=user, status=PENDING)

class OpenFriendRequestView(APIView):

    def post(self, request, *args, **kwargs):
        from_id = request.query_params.get('from')
        to_id = request.query_params.get('to')

        # Check if both 'from' and 'to' parameters are provided
        if not from_id or not to_id:
            return Response(
                {"detail": "Both 'from' and 'to' parameters are required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sender = User.objects.get(id=from_id)
            receiver = User.objects.get(id=to_id)

            # Ensure sender and receiver are different
            if sender == receiver:
                return Response(
                    {"detail": "Sender and receiver cannot be the same."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            friend_request = FriendRequest.objects.create(sender=sender, receiver=receiver)

            return Response(
                {"detail": "Friend request sent successfully."}, 
                status=status.HTTP_201_CREATED
            )

        except User.DoesNotExist:
            return Response(
                {"detail": "One or both users not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        

class FriendRequestDestroyView(generics.DestroyAPIView):
    queryset = FriendRequest.objects.all()
    serializer_class = FriendRequestListView

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
            {'detail': "FRequest removed successfully."},
            status=status.HTTP_200_OK
        )
        

class ResolveFriendRequestView(views.APIView):
    def post(self, request, *args, **kwargs):
        request_id = request.query_params.get('id')
        accepted = request.query_params.get('accepted')

        # Validate request parameters
        if request_id is None or accepted is None:
            return Response({"detail": "Both 'id' and 'accepted' parameters are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate accepted parameter
        try:
            accepted = bool(int(accepted))
        except ValueError:
            return Response({"detail": "'accepted' parameter must be '1' or '0'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the friend request object
            friend_request = FriendRequest.objects.get(id=request_id)
        except FriendRequest.DoesNotExist:
            return Response({"detail": "Friend request not found."}, status=status.HTTP_404_NOT_FOUND)

        # Update the status of the friend request
        if accepted:
            friend_request.status = 1  # Accepted
            
            # Add users to each other's friends
            friend_request.sender.friends.add(friend_request.receiver)
            friend_request.receiver.friends.add(friend_request.sender)
        else:
            friend_request.status = 2  # Rejected

        # Save the updated friend request
        friend_request.save()

        return Response({"detail": "Friend request resolved successfully."}, status=status.HTTP_200_OK)