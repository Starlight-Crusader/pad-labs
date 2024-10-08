from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from users.models import User
from rest_framework_simplejwt.tokens import AccessToken
from unittest.mock import patch
from rest_framework.exceptions import ErrorDetail


class ValidateTokenForBViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username="username0")
        self.url = reverse('validate-token')

        self.token = str(AccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_validate_token_success(self, mock_permission):
        mock_permission.return_value = True

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.user.id)

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_validate_token_no_authentication(self, mock_permission):
        mock_permission.return_value = True

        # Remove authentication credentials
        self.client.credentials()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_validate_token_invalid_user(self, mock_permission):
        mock_permission.return_value = True

        # Try to use token for a non-existent user
        self.user.delete()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_validate_token_unauthorized(self, mock_permission):
        mock_permission.return_value = False

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIsInstance(response.data['detail'], ErrorDetail)