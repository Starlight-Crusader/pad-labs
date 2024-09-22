from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
import os
import requests


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
        try:
            response = requests.get(f'{os.getenv('A_BASE_URL')}api/utilities/validate-token', headers={
                'Authorization': request.headers.get('Authorization'),  # Pass the token
                'X-Root-Password': os.getenv('ROOT_PASSWORD')
            })
            
            if response.status_code == 200:
                request.basic_user_info = response.json()
                return True
        except requests.RequestException:
            return False
        
        return False
