from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from demo.tests.helpers import create_superuser


class SuperAdminLoginTests(TestCase):
    password = "LocalPassword-123!"

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.admin = create_superuser(password=self.password)

    def csrf(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", self.client.cookies)
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Permissions-Policy"], "camera=(), geolocation=(), microphone=()")
        self.assertEqual(response["Cache-Control"], "no-store")
        return self.client.cookies["csrftoken"].value

    def login(self, **overrides):
        payload = {"identifier": self.admin.email, "password": self.password}
        payload.update(overrides)
        return self.client.post(
            "/api/auth/login/", payload, format="json", HTTP_X_CSRFTOKEN=self.csrf()
        )

    def test_active_superuser_can_log_in_with_bcrypt_password_and_refresh_cookie(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertTrue(self.admin.password.startswith("bcrypt_sha256$"))
        cookie = response.cookies["sentinel_refresh"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_invalid_and_non_superuser_logins_share_the_same_generic_response(self):
        ordinary = get_user_model().objects.create_user(
            username="ordinary", email="ordinary@example.test", password=self.password
        )
        bad_password = self.login(password="incorrect-password")
        ordinary_response = self.login(identifier=ordinary.email)

        self.assertEqual(bad_password.status_code, 401)
        self.assertEqual(ordinary_response.status_code, 401)
        self.assertEqual(bad_password.data, ordinary_response.data)
        self.assertEqual(bad_password.data, {"error": {"code": "invalid_credentials"}})

    def test_csrf_is_required_for_cookie_bound_auth_endpoints(self):
        response = APIClient(enforce_csrf_checks=True).post(
            "/api/auth/login/", {"identifier": self.admin.email, "password": self.password}, format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_cross_site_origin_is_refused_even_with_a_valid_csrf_token(self):
        response = self.client.post(
            "/api/auth/login/",
            {"identifier": self.admin.email, "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf(),
            HTTP_ORIGIN="https://untrusted.example",
        )

        self.assertEqual(response.status_code, 403)

    def test_username_is_accepted_as_an_alternative_to_email(self):
        response = self.login(identifier=self.admin.username)

        self.assertEqual(response.status_code, 200)

    def test_refresh_rotation_and_logout_blacklist_the_active_refresh_token(self):
        login = self.login()
        original = login.cookies["sentinel_refresh"].value
        refreshed = self.client.post("/api/auth/refresh/", {}, format="json", HTTP_X_CSRFTOKEN=self.csrf())

        self.assertEqual(refreshed.status_code, 200)
        self.assertNotEqual(original, refreshed.cookies["sentinel_refresh"].value)
        logout = self.client.post("/api/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(logout.cookies["sentinel_refresh"]["max-age"], 0)
