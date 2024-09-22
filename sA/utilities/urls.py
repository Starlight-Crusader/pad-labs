from django.urls import path
from .views import ValidateTokenForBView, StatusView


urlpatterns = [
    path('validate-token', ValidateTokenForBView.as_view(),  name='validate-token'),
    path('status', StatusView.as_view(), name='status'),
]