from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response

from submissions.utils import sanitize_single_line
from submissions.api.throttles import LoginIPThrottle, LoginUsernameThrottle


def _serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"detail": "CSRF cookie set."})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([LoginIPThrottle, LoginUsernameThrottle])
@csrf_protect
def login_view(request):
    raw_username = request.data.get("username")
    password = request.data.get("password")
    if not isinstance(raw_username, str) or not isinstance(password, str):
        return Response(
            {"message": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    username = sanitize_single_line(raw_username)

    if not username or not password or len(username) > 150 or len(password) > 1024:
        return Response(
            {"message": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_staff:
        return Response(
            {"message": "Invalid username or password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    login(request, user)
    return Response({"user": _serialize_user(user)})


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response({"detail": "Logged out."})


@api_view(["GET"])
def session_view(request):
    user = request.user
    if not user.is_authenticated:
        return Response({"authenticated": False})

    return Response(
        {
            "authenticated": True,
            "user": _serialize_user(user),
        }
    )
