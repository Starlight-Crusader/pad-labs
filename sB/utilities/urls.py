from django.urls import path
from .views import StatusView


urlpatterns = [
    path('status', StatusView.as_view(), name='status'),
]