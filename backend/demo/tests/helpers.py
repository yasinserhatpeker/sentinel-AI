from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken


def create_superuser(email="admin@example.test", password="LocalPassword-123!"):
    return get_user_model().objects.create_superuser(
        username=email,
        email=email,
        password=password,
    )


def bearer_token(user):
    return f"Bearer {AccessToken.for_user(user)}"
