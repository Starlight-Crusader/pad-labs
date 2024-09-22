from django.urls import path
from .views import GameRecordListView, SaveGameRecordView


urlpatterns = [
    path('list', GameRecordListView.as_view(), name='gr-list'),
    path('save', SaveGameRecordView.as_view(), name='gr-save')
]