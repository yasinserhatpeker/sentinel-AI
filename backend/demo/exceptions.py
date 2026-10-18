from rest_framework import exceptions
from rest_framework.views import exception_handler


def demo_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, exceptions.ValidationError):
            detail = "validation_failed"
        else:
            detail = response.data.get("detail", "request_failed")
        response.data = {"error": {"code": str(detail)}}
    return response

