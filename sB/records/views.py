from rest_framework import generics, response, status
from .models import GameRecord
from .serializers import GameRecordSerializer
from django.db.models import Q
from sB.permissions import ProvidesValidRootPassword
from rest_framework import serializers
from rest_framework.views import APIView
from django.db import models


class GameRecordListView(generics.ListAPIView):
    serializer_class = GameRecordSerializer
    
    def get_queryset(self):
        record_id = self.request.query_params.get('id', None)

        if record_id:
            return GameRecord.objects.filter(id=record_id)

        username = self.request.query_params.get('uname', None)

        if username:
            return GameRecord.objects.filter(
                Q(white_player=username) | Q(black_player=username)
            )
        else:
            return GameRecord.objects.all()
    

class SaveGameRecordView(generics.CreateAPIView):
    queryset = GameRecord.objects.all()
    serializer_class = GameRecordSerializer
    permission_classes = [ProvidesValidRootPassword]

    def create(self, request, *args, **kwargs):
        # Check if the data is a list
        if not isinstance(request.data, list):
            return response.Response(
                {"detail": f"Request data must be a list of rec."}, 
                status=status.HTTP_201_CREATED
            )

        # Create serializer for multiple records
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return response.Response(
            {"message": f"Successfully created {len(serializer.data)} rec."}, 
            status=status.HTTP_201_CREATED
        )
    

class BulkDeleteGameRecordsView(APIView):
    permission_classes = [ProvidesValidRootPassword]

    def delete(self, request, *args, **kwargs):
        # Get all records before deletion
        games = GameRecord.objects.all()
        
        # Count records
        deletion_count = games.count()
        
        # Delete all records
        games.delete()

        # Return the deleted records data
        return response.Response({
            "message": f"Successfully deleted all {deletion_count} game records."
        }, status=status.HTTP_200_OK)
    

class DeleteAllGameRecordsByUsernameView(generics.DestroyAPIView):
    queryset = GameRecord.objects.all()
    permission_classes = [ProvidesValidRootPassword]

    def delete(self, request, *args, **kwargs):
        username = request.query_params.get('username')
        if not username:
            return response.Response(
                { "detail": "user_id query parameter is required." }, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find all games where the user was either white or black player
        games = GameRecord.objects.filter(
            models.Q(white_player=username) | 
            models.Q(black_player=username)
        )

        if len(games) == 0:
            return response.Response(
                { "message": "No associated games found." }, 
                status=status.HTTP_202_ACCEPTED
            )

        # Store the games data before deletion
        games_data = list(games.values())
        
        # Delete the games
        deletion_count = games.delete()[0]

        # Return the deleted games data
        return response.Response(
            {
                "message": f"Successfully deleted {deletion_count} game records for user {username}.",
                "deleted_records": games_data
            }, 
            status=status.HTTP_200_OK
        )