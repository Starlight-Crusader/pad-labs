from django.urls import path
from .views import GameRecordListView, SaveGameRecordView, BulkDeleteGameRecordsView, DeleteAllGameRecordsByUsernameView


urlpatterns = [
    path('list', GameRecordListView.as_view(), name='gr-list'),
    path('save', SaveGameRecordView.as_view(), name='gr-save'),
    path('bulk-delete', BulkDeleteGameRecordsView.as_view(), name='b-delete'),
    path('user-delete', DeleteAllGameRecordsByUsernameView.as_view(), name='u-delete'),
]