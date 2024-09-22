from django.urls import path
from .views import UserSearchView, OpenFriendRequestView, FriendRequestListView, ReceivedFriendRequestsListView, ResolveFriendRequestView, FriendRequestDestroyView, UserFriendsIdsListView


urlpatterns = [
    path('search/', UserSearchView.as_view(), name='friend-search'),
    path('requests/open/', OpenFriendRequestView.as_view(), name='friend-requests-open'),
    path('requests/list/all/', FriendRequestListView.as_view(), name='friend-requests-list-all'),
    path('requests/list/my/', ReceivedFriendRequestsListView.as_view(), name='friend-requests-list-my'),
    path('requests/resolve/', ResolveFriendRequestView.as_view(), name='friend-request-resolve'),
    path('requests/<int:pk>/destroy/', FriendRequestDestroyView.as_view(), name='friend-request-destroy'),
    path('get-ids/', UserFriendsIdsListView.as_view(), name='friend-get-ids')
]