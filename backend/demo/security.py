class SecurityHeadersMiddleware:
    """Apply browser hardening headers to API responses served by Django."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        response.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response
