from django.urls import path
from .views import UserListView, UserDestroyView, UserUpdateRatingView


urlpatterns = [
    path('list', UserListView.as_view(), name='user-list'),
    path('<int:pk>/destroy', UserDestroyView.as_view(), name='user-destroy'),
    path('rating/upd', UserUpdateRatingView.as_view(), name='user-rating-upd'),
]