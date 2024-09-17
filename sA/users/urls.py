from django.urls import path
from .views import UserCreateView, UserListView, UserDestroyView, UserUpdateRatingView, UserSearchView


urlpatterns = [
    path('list/', UserListView.as_view(), name='user-list'),
    path('create/', UserCreateView.as_view(), name='user-create'),
    path('<int:pk>/destroy/', UserDestroyView.as_view(), name='user-destroy'),
    path('rating/upd/', UserUpdateRatingView.as_view(), name='user-rating-upd'),
    path('search/', UserSearchView.as_view(), name='user-search')
]