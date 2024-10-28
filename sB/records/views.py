from rest_framework import generics, response, status
from .models import GameRecord
from .serializers import GameRecordSerializer
from sB.permissions import ValidateTokenWithServiceA
from django.db.models import Q


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
    permission_classes = [ValidateTokenWithServiceA]

    def create(self, request, *args, **kwargs):
        # Call the original create method to save the game record
        super().create(request, *args, **kwargs)
        
        # Return a custom response with a confirmation message
        return response.Response(
            {"message": "Game record saved successfully."},
            status=status.HTTP_201_CREATED
        )