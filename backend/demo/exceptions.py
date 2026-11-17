from rest_framework import exceptions
from rest_framework.views import exception_handler


class AnalysisReadinessConflict(exceptions.APIException):
    """A safe, retryable analysis operation whose real-data gate is not ready."""

    status_code = 409
    default_detail = "analysis_not_ready"
    default_code = "analysis_not_ready"


def demo_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, exceptions.ValidationError):
            detail = "validation_failed"
        elif isinstance(exc, exceptions.NotAuthenticated):
            detail = "authentication_required"
        else:
            detail = response.data.get("detail", "request_failed")
        response.data = {"error": {"code": str(detail)}}
    return response

