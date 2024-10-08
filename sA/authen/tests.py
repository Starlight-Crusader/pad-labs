from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User


class SignUpViewTest(APITestCase):
    def setUp(self):
        self.valid_payload = {
            'username': "username1",
            'password': "username1password"
        }

        self.invalid_payload_missing_field = {
            'username': "username2",
            'password': ""
        }

        self.invalid_payload_bad_password = {
            'username': "username3",
            'password': "123"
        }

    def test_create_user(self):
        url = reverse('signup')
        response = self.client.post(url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('detail' in response.data)
        self.assertIn('user' in response.data)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'username1')

    def test_create_user_missing_field(self):
        url = reverse('signup')
        response = self.client.post(url, self.invalid_payload_missing_password, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username' in response.data or 'password' in response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_create_user_bad_password(self):
        url = reverse('signup')
        response = self.client.post(url, self.invalid_payload_missing_password, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password' in response.data)
        self.assertEqual(User.objects.count(), 0)


class SignInViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='username0', password='username0password'
        )

    def test_sign_in_success(self):
        url = reverse('signin')
        response = self.client.post(url, {'username': 'username0', 'password': 'username0password'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)