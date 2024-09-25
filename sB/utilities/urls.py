from django.urls import path
from .views import StatusView


urlpatterns = [
    path('ping', StatusView.as_view(), name='ping'),
]