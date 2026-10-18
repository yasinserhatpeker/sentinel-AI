from dataclasses import dataclass

from django.conf import settings
from rest_framework import authentication, exceptions


@dataclass(frozen=True)
class DemoPrincipal:
    """Non-persistent principal for local-only demo API access."""

    username: str = "local-demo"
    is_authenticated: bool = True


class DemoTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Demo"

    def authenticate(self, request):
        value = authentication.get_authorization_header(request).decode("utf-8")
        prefix = f"{self.keyword} "
        if not value.startswith(prefix):
            raise exceptions.AuthenticationFailed("demo_token_required")

        token = value.removeprefix(prefix)
        if token != settings.DEMO_API_TOKEN:
            raise exceptions.AuthenticationFailed("demo_token_invalid")

        return DemoPrincipal(), token

    def authenticate_header(self, request):
        return self.keyword
