from rest_framework import permissions
from .models import Notification

class IsSelfOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow users to edit their own profile,
    or admins to edit any profile.
    """
    def has_object_permission(self, request, view, obj):
        return obj == request.user or request.user.is_staff

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # For different models, check different owner fields
        if isinstance(obj, Notification):
            return obj.recipient == request.user
        elif hasattr(obj, 'author'):
            return obj.author == request.user
        return False

class IsRegistered(permissions.BasePermission):
    """
    Allows access only to authenticated users (registered users).
    """
    message = "Authentication required to access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class IsAuthenticatedUnverified(permissions.BasePermission):
    """
    Allows access only to authenticated but not yet verified users.
    Useful for actions like submitting verification requests.
    """
    message = "User must be logged in but not yet verified."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            not getattr(request.user, 'is_verified_user', False)
        )


class IsAuthenticatedAndVerified(permissions.BasePermission):
    """
    Allows access only to authenticated and verified users.
    """
    message = "User verification required to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'is_verified_user', False)
        )


class IsOwnerOrReadOnlyVerified(permissions.BasePermission):
    """
    Allows safe methods for everyone, write methods only for the verified owner.
    Assumes the object has an 'author' attribute.
    """
    message = "Only the verified owner can modify this object."

    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        # For write methods, require authenticated and verified
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'is_verified_user', False)
        )

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to the owner
        return bool(
            hasattr(obj, 'author') and
            obj.author == request.user
        )
