import hashlib

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class PublicAuthAPIView(APIView):
    """Public endpoints that still return a standards-compliant 401 challenge."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get_authenticate_header(self, request):
        return "Bearer"


def _limit_key(request, identifier):
    value = f"{request.META.get('REMOTE_ADDR', '')}:{identifier.lower()}"
    return f"login-limit:{hashlib.sha256(value.encode()).hexdigest()}"


def _assert_same_site(request):
    """Reject explicitly cross-site unsafe requests before handling cookies."""
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        raise PermissionDenied("authentication_required")
    origin = request.headers.get("Origin")
    if origin and origin not in {"http://localhost:5174"}:
        raise PermissionDenied("authentication_required")


def _set_refresh_cookie(response, refresh):
    response.set_cookie(
        "sentinel_refresh",
        str(refresh),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/api/auth/",
        max_age=86400,
    )
    response["Cache-Control"] = "no-store"
    return response


class CsrfView(PublicAuthAPIView):

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        response = Response({"csrfToken": get_token(request)})
        response["Cache-Control"] = "no-store"
        return response


@method_decorator(csrf_protect, name="dispatch")
class LoginView(PublicAuthAPIView):

    def post(self, request):
        _assert_same_site(request)
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            raise AuthenticationFailed("invalid_credentials")
        identifier = serializer.validated_data["identifier"]
        key = _limit_key(request, identifier)
        if cache.get(key, 0) >= 5:
            raise AuthenticationFailed("invalid_credentials")
        user = authenticate(request, identifier=identifier, password=serializer.validated_data["password"])
        if user is None or not user.is_active or not user.is_superuser:
            cache.set(key, cache.get(key, 0) + 1, timeout=900)
            raise AuthenticationFailed("invalid_credentials")
        cache.delete(key)
        refresh = RefreshToken.for_user(user)
        return _set_refresh_cookie(Response({"access": str(refresh.access_token)}), refresh)


@method_decorator(csrf_protect, name="dispatch")
class RefreshView(PublicAuthAPIView):

    def post(self, request):
        _assert_same_site(request)
        value = request.COOKIES.get("sentinel_refresh")
        if not value:
            raise AuthenticationFailed("authentication_required")
        try:
            refresh = RefreshToken(value)
            refresh.blacklist()
            user = get_user_model().objects.get(pk=refresh["user_id"])
            if not user.is_active or not user.is_superuser:
                raise PermissionDenied("authentication_required")
            next_refresh = RefreshToken.for_user(user)
        except Exception as error:
            raise AuthenticationFailed("authentication_required") from error
        return _set_refresh_cookie(Response({"access": str(next_refresh.access_token)}), next_refresh)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(PublicAuthAPIView):

    def post(self, request):
        _assert_same_site(request)
        value = request.COOKIES.get("sentinel_refresh")
        if value:
            try:
                RefreshToken(value).blacklist()
            except Exception:
                pass
        response = Response(status=204)
        response.delete_cookie("sentinel_refresh", path="/api/auth/")
        response["Cache-Control"] = "no-store"
        return response
