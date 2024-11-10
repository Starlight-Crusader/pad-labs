from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
import os
import requests
from .utilities import get_timeout_from_token, cache_get, cache_set


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

        user_data = self.fetch_user_data_by_token(full_token_str)
        if user_data:
            request.user_data = user_data
            return True
        
        return False
    
    def fetch_user_data_by_token(self, full_token_str):
        token = full_token_str.split(' ')[1]

        # Check the cache first
        cached_user_data = cache_get(token + "_user_data")
        if cached_user_data:
            print(f"LOG: Using cached basic user info for user#{cached_user_data.get('id')}")
            return cached_user_data

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
                user_data = response.json()
                self.cache_user_data(token, user_data)
                return user_data
        except requests.RequestException as e:
            print(f"Request failed: {e}")

        return None

    def cache_user_data(self, token, user_data):
        timeout = get_timeout_from_token(token)

        if timeout is not None:
            cache_set(token + "_user_data", user_data, timeout=timeout)
            print(f"LOG: Cached basic user info for user#{user_data.get('id')}")
