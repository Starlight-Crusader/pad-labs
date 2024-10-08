from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
from .models import FriendRequest


class UserSearchViewTest(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create(username="username0")
        self.user2 = User.objects.create(username="username1")
    
    def test_search_existing_user(self):
        url = reverse('friend-search')
        response = self.client.get(url, {'uname': '0'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'username0')
    
    def test_search_no_results(self):
        url = reverse('friend-search')
        response = self.client.get(url, {'uname': '9999'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class ReceivedFriendRequestsListViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username="receiver")
        self.client.force_authenticate(user=self.user)

        FriendRequest.objects.create(
            sender=User.objects.create(username="sender"),
            receiver=self.user
        )

        self.url = reverse('friend-requests-list-my')

    def test_list_received_friend_requests(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class OpenFriendRequestViewTest(APITestCase):
    def setUp(self):
        self.sender = User.objects.create(username="sender")
        self.receiver = User.objects.create(username="receiver")

        self.client.force_authenticate(user=self.sender)

        self.url = reverse('friend-requests-open')

    def test_send_friend_request(self):
        response = self.client.post(f'{self.url}?to={self.receiver.id}')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FriendRequest.objects.count(), 1)
        self.assertEqual(FriendRequest.objects.all()[0].sender, self.sender)
        self.assertEqual(FriendRequest.objects.all()[0].receiver, self.receiver)

    def test_send_friend_request_to_self(self):
        response = self.client.post(f'{self.url}?to={self.sender.id}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(FriendRequest.objects.count(), 0)

    def test_send_friend_request_missing_param(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(FriendRequest.objects.count(), 0)