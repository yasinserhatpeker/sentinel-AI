"""Bounded, local-only HTTP client for causal demo-service workflows."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyResponse:
    status_code: int
    body: dict[str, object]


class DependencyRequestError(RuntimeError):
    def __init__(self, dependency: str, status_code: int | None = None) -> None:
        super().__init__(f"dependency_request_failed:{dependency}")
        self.dependency = dependency
        self.status_code = status_code


def post_json(url: str, payload: dict[str, object], correlation_id: str, dependency: str) -> DependencyResponse:
    """Call a Compose-internal dependency with bounded payload, time and error shape."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Correlation-ID": correlation_id},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            raw_body = response.read(16_384)
            body = json.loads(raw_body.decode() or "{}")
            return DependencyResponse(response.status, body if isinstance(body, dict) else {})
    except urllib.error.HTTPError as error:
        raise DependencyRequestError(dependency, error.code) from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise DependencyRequestError(dependency) from None
