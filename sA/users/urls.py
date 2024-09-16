from django.urls import path
from .views import UserCreateView, UserListView, UserDestroyView, UpdateUserRatingView


urlpatterns = [
    path('list/', UserListView.as_view(), name='user-list'),
    path('create/', UserCreateView.as_view(), name='user-create'),
    path('<int:pk>/delete/', UserDestroyView.as_view(), name='user-delete'),
    path('rating/upd/', UpdateUserRatingView.as_view(), name='update-user-rating'),
]