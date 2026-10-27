"""Authentication for local demo services, kept separate from human JWT sessions."""

from __future__ import annotations

import secrets
import hashlib
import hmac
from dataclasses import dataclass

from django.conf import settings
from rest_framework import authentication, exceptions


@dataclass(frozen=True)
class DemoServicePrincipal:
    """Minimal authenticated identity; it deliberately has no Django permissions."""

    name: str = "local-demo-telemetry"
    is_authenticated: bool = True


class DemoTelemetryTokenAuthentication(authentication.BaseAuthentication):
    """Accept a local machine signature derived from the Django secret, never a browser session."""

    header_name = "HTTP_X_TELEMETRY_SIGNATURE"

    @staticmethod
    def expected_signature() -> str:
        return hmac.new(
            settings.SECRET_KEY.encode(), b"sentinelai-local-telemetry-v1", hashlib.sha256
        ).hexdigest()

    def authenticate(self, request):
        supplied = request.META.get(self.header_name)
        if supplied is None:
            return None

        if not secrets.compare_digest(supplied, self.expected_signature()):
            raise exceptions.AuthenticationFailed("authentication_failed")
        return (DemoServicePrincipal(), None)

    def authenticate_header(self, _request) -> str:
        return "SentinelAI-HMAC"
