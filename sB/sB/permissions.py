from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
import os
import requests
import jwt
from django.core.cache import cache
from .utilities import get_timeout_from_token


class ProvidesValidRootPassword(BasePermission):

    def has_permission(self, request, view):
        # Extract password from headers
        password = request.headers.get('X-Root-Password')

        # Check if password is provided
        if not password:
            raise PermissionDenied(detail="Authorization credentials are missing.")

        # Verify the password against the environment variable
        if password != os.getenv('ROOT_PASSWORD'):
            raise PermissionDenied(detail="Authorization credentials are invalid.")

        # If the password is valid, grant access
        return True


class ValidateTokenWithServiceA(BasePermission):

    def has_permission(self, request, view):
        full_token_str = request.headers.get('Authorization')

        user_info = self.get_user_info(full_token_str)
        if user_info:
            request.basic_user_info = user_info
            return True
        
        return False

    def get_user_info(self, full_token_str):
        token = full_token_str.split(' ')[1]

        # Check the cache first
        cached_basic_user_info = cache.get(token + "_basic_user_info")
        if cached_basic_user_info:
            print("Using cached basic user info")
            return cached_basic_user_info

        try:
            # Make the request to Service A to validate the token
            response = requests.get(
                f'{os.getenv('API_GATEWAY_BASE_URL')}sA/api/utilities/validate-token',
                headers={
                    'Authorization': full_token_str,
                    'X-Root-Password': os.getenv('ROOT_PASSWORD')
                }
            )

            if response.status_code == 200:
                user_info = response.json()
                self.cache_basic_user_info(token, user_info)
                return user_info
        except requests.RequestException as e:
            print(f"Request failed: {e}")

        return None

    def cache_basic_user_info(self, token, basic_user_info):
        timeout = get_timeout_from_token(token)

        if timeout is not None:
            cache.set(token + "_basic_user_info", basic_user_info, timeout=timeout)
            print("Cached token verification")
