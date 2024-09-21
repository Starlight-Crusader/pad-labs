from rest_framework import generics
from .models import GameRecord
from .serializers import GameRecordSerializer
from sB.permissions import ProvidesValidRootPassword, ValidateTokenWithServiceA
from django.db.models import Q


class GameRecordListView(generics.ListAPIView):
    serializer_class = GameRecordSerializer
    
    def get_queryset(self):
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