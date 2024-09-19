from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
import os


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
    pass