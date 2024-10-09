from django.urls import path
from .views import ValidateTokenForBView, StatusView, SleepyView


urlpatterns = [
    path('validate-token', ValidateTokenForBView.as_view(),  name='validate-token'),
    path('ping', StatusView.as_view(), name='ping'),
    path('sleepy', SleepyView.as_view(), name='sleepy'),
]