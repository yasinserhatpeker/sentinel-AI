"""Signed local-only fault control endpoint shared by demo services."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .fault import FaultStateUnavailable, active_fault, start_fault, stop_fault


def _valid_signature(body: bytes, timestamp: str, signature: str) -> bool:
    try:
        request_time = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - request_time) > 30:
        return False
    secret = os.environ.get("DJANGO_SECRET_KEY", "")
    if not secret:
        return False
    message = b"sentinelai-fault-control-v1." + timestamp.encode() + b"." + body
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@csrf_exempt
def fault_control(request):
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    if not _valid_signature(request.body, request.headers.get("X-Fault-Timestamp", ""), request.headers.get("X-Fault-Signature", "")):
        return JsonResponse({"error": "fault_signature_invalid"}, status=403)
    try:
        payload = json.loads(request.body)
        action = payload.get("action")
        if action == "start":
            state = start_fault(payload)
            return JsonResponse({"status": "active", "experiment_id": state["experiment_id"], "expires_at": state["expires_at"]})
        if action == "stop":
            stopped = stop_fault(str(payload.get("experiment_id", "")))
            return JsonResponse({"status": "stopped", "changed": stopped})
        if action == "status":
            state = active_fault()
            return JsonResponse({"status": "active" if state else "idle", "experiment_id": state.get("experiment_id") if state else None})
        return JsonResponse({"error": "fault_action_invalid"}, status=400)
    except FaultStateUnavailable as error:
        return JsonResponse({"error": str(error)}, status=503)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return JsonResponse({"error": str(error)}, status=400)
