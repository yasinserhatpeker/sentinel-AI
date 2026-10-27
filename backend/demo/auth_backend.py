from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate the local Django user model by username or case-insensitive email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (kwargs.get("identifier") or username or "").strip()
        if not identifier or password is None:
            return None
        try:
            user = get_user_model().objects.get(email__iexact=identifier)
        except get_user_model().DoesNotExist:
            try:
                user = get_user_model().objects.get(username=identifier)
            except get_user_model().DoesNotExist:
                # Keep password-check timing similar for unknown accounts.
                get_user_model()().set_password(password)
                return None
        except get_user_model().MultipleObjectsReturned:
            return None
        return user if user.check_password(password) and self.user_can_authenticate(user) else None
