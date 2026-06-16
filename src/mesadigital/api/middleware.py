import json
import logging
import time
import uuid
from typing import Any

import sentry_sdk
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("mesadigital.api.access")

_RESTAURANT_PARAM_NAMES = frozenset({"rid", "restaurant_id"})


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        status_code: int = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        t0 = time.perf_counter()
        with sentry_sdk.new_scope() as sentry_scope:
            sentry_scope.set_tag("request_id", request_id)
            await self.app(scope, receive, send_wrapper)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        path_params: dict[str, Any] = scope.get("path_params", {})
        restaurant_id: str | None = next(
            (path_params[k] for k in _RESTAURANT_PARAM_NAMES if k in path_params),
            None,
        )

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "restaurant_id": restaurant_id,
                }
            )
        )
