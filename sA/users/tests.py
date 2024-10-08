from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
from unittest.mock import patch


class UserUpdateRatingViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username="username")
        self.url = reverse('user-rating-upd')

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_update_user_rating_success(self, mock_permission):
        mock_permission.return_value = True

        response = self.client.patch(f'{self.url}?id={self.user.id}&delta=100')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.rating, 1300)

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_update_user_rating_missing_params(self, mock_permission):
        mock_permission.return_value = True

        response = self.client.patch(f'{self.url}?id={self.user.id}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "Both 'id' and 'delta' query parameters are required!")

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_update_user_rating_invalid_delta(self, mock_permission):
        mock_permission.return_value = True

        response = self.client.patch(f'{self.url}?id={self.user.id}&delta=abc')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "'delta' must be an integer!")

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_update_rating_user_not_found(self, mock_permission):
        mock_permission.return_value = True

        response = self.client.patch(f'{self.url}?id=9999&delta=100')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], "User not found!")

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_update_rating_unauthorized(self, mock_permission):
        mock_permission.return_value = False

        response = self.client.patch(f'{self.url}?id=1&delta=100')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], "Authentication credentials were not provided.")
