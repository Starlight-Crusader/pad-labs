from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from users import models


class SignUpViewTest(APITestCase):
    def setUp(self):
        self.valid_payload = {
            'username': "username0",
            'password': "username0password"
        }

        self.invalid_payload_missing_password = {
            'username': "username0",
            'password': ""
        }

        self.invalid_payload_bad_password = {
            'username': "username0",
            'password': "000"
        }

    def test_create_user(self):
        url = reverse('signup')
        response = self.client.post(url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('detail', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, 'username0')

    def test_create_user_missing_password(self):
        url = reverse('signup')
        response = self.client.post(url, self.invalid_payload_missing_password, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertEqual(models.User.objects.count(), 0)

    def test_create_user_bad_password(self):
        url = reverse('signup')
        response = self.client.post(url, self.invalid_payload_bad_password, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertEqual(models.User.objects.count(), 0)


class SignInViewTest(APITestCase):
    def setUp(self):
        self.user = models.User.objects.create(username='username0')
        self.user.set_password('username0password')
        self.user.save()

    def test_sign_in_success(self):
        url = reverse('signin')
        response = self.client.post(url, {'username': 'username0', 'password': 'username0password'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_sign_in_invalid_credentials(self):
        url = reverse('signin')
        response = self.client.post(url, {'username': 'usernameUnknown', 'password': 'usernameUnknownPassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Invalid credentials.')


class IssueAccessTokenByIdViewTests(APITestCase):
    def setUp(self):
        self.user = models.User.objects.create(username='username0')
        self.user.set_password('username0password')
        self.user.save()

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_issue_access_token_success(self, mock_permission):
        mock_permission.return_value = True

        url = reverse('token-by-id', kwargs={'user_id': self.user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_issue_access_token_user_not_found(self, mock_permission):
        mock_permission.return_value = True

        url = reverse('token-by-id', kwargs={'user_id': 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'User not found.')

    @patch('sA.permissions.ProvidesValidRootPassword.has_permission')
    def test_permission_denied(self, mock_permission):
        mock_permission.return_value = False

        url = reverse('token-by-id', kwargs={'user_id': self.user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
