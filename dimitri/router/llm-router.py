#!/usr/bin/env python3
"""LLM Router v2 — Hybrid DeepSeek + Qwen with automatic fallback.

Routes based on model name:
  - "deepseek*" → DeepSeek API (remote, smart orchestration)
  - anything else → Qwen local (fast execution)

If DeepSeek fails (timeout, 5xx, connection error):
  → Automatically retries with Qwen local (degraded but functional)

Health endpoint monitors both backends.
"""

import asyncio
import json
import logging
import os
import ssl
import sys
import time

from aiohttp import web, ClientSession, ClientTimeout, TCPConnector
from aiohttp.resolver import ThreadedResolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("llm-router")

# --- Config ---
LISTEN_PORT = int(os.environ.get("ROUTER_PORT", "8090"))
QWEN_URL = os.environ.get("QWEN_URL", "http://localhost:8080")
DEEPSEEK_URL = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen3-coder-30b")

TIMEOUT_DEEPSEEK = ClientTimeout(total=45, connect=10, sock_connect=10, sock_read=35)
TIMEOUT_QWEN = ClientTimeout(total=300, connect=10, sock_connect=10, sock_read=240)

# --- Health tracking ---
_deepseek_ok = True
_deepseek_last_fail = 0.0
_deepseek_fail_count = 0
DEEPSEEK_BACKOFF_BASE = 30  # seconds before retrying after failure


def is_deepseek_model(model: str) -> bool:
    return "deepseek" in (model or "").lower()


def pick_backend(model: str):
    """Return (base_url, extra_headers, timeout, is_deepseek)."""
    if is_deepseek_model(model):
        return DEEPSEEK_URL, {"Authorization": "Bearer " + DEEPSEEK_KEY}, TIMEOUT_DEEPSEEK, True
    return QWEN_URL, {}, TIMEOUT_QWEN, False


def clean_model_name(model: str) -> str:
    """Strip provider prefix: 'openai/deepseek-chat' → 'deepseek-chat'."""
    if "/" in model:
        return model.split("/", 1)[1]
    return model


def make_connector(https: bool):
    ssl_ctx = ssl.create_default_context() if https else None
    return TCPConnector(ssl=ssl_ctx, force_close=True, resolver=ThreadedResolver())


async def do_request(session, method, target, headers, body_bytes, is_stream):
    """Execute the actual HTTP request and return a web.Response or web.StreamResponse."""
    async with session.request(method, target, headers=headers, data=body_bytes) as resp:
        if is_stream:
            response = web.StreamResponse(
                status=resp.status,
                headers={
                    "Content-Type": resp.headers.get("Content-Type", "text/event-stream"),
                    "Cache-Control": "no-cache",
                },
            )
            await response.prepare(None)  # Will be set by caller
            return resp, response  # Caller handles streaming
        else:
            resp_body = await resp.read()
            ct = resp.headers.get("Content-Type", "application/json")
            ct_clean = ct.split(";")[0].strip()
            return resp.status, resp_body, ct_clean


async def proxy_handler(request: web.Request) -> web.StreamResponse:
    """Proxy any /v1/* request to the right backend, with fallback."""
    global _deepseek_ok, _deepseek_last_fail, _deepseek_fail_count

    path = request.path
    body_bytes = await request.read()

    # Parse model from body
    model = "unknown"
    body_json = None
    try:
        body_json = json.loads(body_bytes)
        model = body_json.get("model", "unknown")
    except Exception:
        pass

    # Clean model name (strip provider prefix)
    clean = clean_model_name(model)
    if body_json and clean != model:
        body_json["model"] = clean
        body_bytes = json.dumps(body_json).encode()
        log.info("  model rewritten: %s → %s", model, clean)

    # Determine backend
    base_url, extra_headers, timeout, is_ds = pick_backend(clean)

    # Check DeepSeek health — if recently failed, skip straight to fallback
    if is_ds and not _deepseek_ok:
        elapsed = time.time() - _deepseek_last_fail
        backoff = DEEPSEEK_BACKOFF_BASE * min(_deepseek_fail_count, 10)
        if elapsed < backoff:
            log.warning("DeepSeek in backoff (%ds left), falling back to Qwen", int(backoff - elapsed))
            base_url = QWEN_URL
            extra_headers = {}
            timeout = TIMEOUT_QWEN
            is_ds = False
            # Rewrite model to Qwen
            if body_json:
                body_json["model"] = QWEN_MODEL
                body_bytes = json.dumps(body_json).encode()
                log.info("  model fallback: %s → %s", clean, QWEN_MODEL)

    # Build headers
    headers = {}
    for k, v in request.headers.items():
        if k.lower() in ("host", "content-length", "transfer-encoding"):
            continue
        headers[k] = v
    headers.update(extra_headers)

    # Detect streaming
    is_stream = False
    try:
        is_stream = (body_json or {}).get("stream", False)
    except Exception:
        pass

    target = base_url + path
    log.info("→ %s → %s %s %s", clean, base_url, request.method, path)

    https = target.startswith("https")
    connector = make_connector(https)
    try:
        async with ClientSession(timeout=timeout, connector=connector) as session:
            try:
                async with session.request(
                    request.method, target, headers=headers, data=body_bytes,
                ) as resp:
                    if is_stream:
                        response = web.StreamResponse(
                            status=resp.status,
                            headers={
                                "Content-Type": resp.headers.get("Content-Type", "text/event-stream"),
                                "Cache-Control": "no-cache",
                            },
                        )
                        await response.prepare(request)
                        async for chunk in resp.content.iter_any():
                            await response.write(chunk)
                        await response.write_eof()

                        # Mark DeepSeek healthy on success
                        if is_ds and resp.status < 400:
                            _deepseek_ok = True
                            _deepseek_fail_count = 0

                        return response
                    else:
                        resp_body = await resp.read()
                        ct = resp.headers.get("Content-Type", "application/json").split(";")[0].strip()

                        # If DeepSeek returned an error, try fallback
                        if is_ds and resp.status >= 400:
                            log.warning("DeepSeek returned %d, falling back to Qwen", resp.status)
                            _deepseek_ok = False
                            _deepseek_last_fail = time.time()
                            _deepseek_fail_count += 1
                            return await _fallback_to_qwen(request, path, body_json, body_bytes, is_stream)

                        # Mark DeepSeek healthy on success
                        if is_ds:
                            _deepseek_ok = True
                            _deepseek_fail_count = 0

                        return web.Response(status=resp.status, body=resp_body, content_type=ct)

            except Exception as e:
                if is_ds:
                    log.error("DeepSeek error: %s — falling back to Qwen", e)
                    _deepseek_ok = False
                    _deepseek_last_fail = time.time()
                    _deepseek_fail_count += 1
                    return await _fallback_to_qwen(request, path, body_json, body_bytes, is_stream)
                else:
                    log.error("Qwen error: %s", e)
                    return web.json_response(
                        {"error": {"message": "Proxy error: %s" % e, "type": "proxy_error"}},
                        status=502,
                    )
    finally:
        await connector.close()


async def _fallback_to_qwen(request, path, body_json, body_bytes, is_stream):
    """Fallback: rewrite model to Qwen and send to local server."""
    if body_json:
        body_json["model"] = QWEN_MODEL
        body_bytes = json.dumps(body_json).encode()
    log.info("  FALLBACK → %s → %s", QWEN_MODEL, QWEN_URL)

    target = QWEN_URL + path
    headers = {}
    for k, v in request.headers.items():
        if k.lower() in ("host", "content-length", "transfer-encoding"):
            continue
        headers[k] = v

    connector = make_connector(False)
    try:
        async with ClientSession(timeout=TIMEOUT_QWEN, connector=connector) as session:
            try:
                async with session.request(
                    request.method, target, headers=headers, data=body_bytes,
                ) as resp:
                    if is_stream:
                        response = web.StreamResponse(
                            status=resp.status,
                            headers={
                                "Content-Type": resp.headers.get("Content-Type", "text/event-stream"),
                                "Cache-Control": "no-cache",
                            },
                        )
                        await response.prepare(request)
                        async for chunk in resp.content.iter_any():
                            await response.write(chunk)
                        await response.write_eof()
                        return response
                    else:
                        resp_body = await resp.read()
                        ct = resp.headers.get("Content-Type", "application/json").split(";")[0].strip()
                        return web.Response(status=resp.status, body=resp_body, content_type=ct)
            except Exception as e:
                log.error("Fallback Qwen also failed: %s", e)
                return web.json_response(
                    {"error": {"message": "Both backends failed. DeepSeek + Qwen down.", "type": "proxy_error"}},
                    status=502,
                )
    finally:
        await connector.close()


async def models_handler(request: web.Request) -> web.Response:
    """Merge models from both backends."""
    models = [
        {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
        {"id": "deepseek-reasoner", "object": "model", "owned_by": "deepseek"},
    ]
    try:
        connector = make_connector(False)
        async with ClientSession(timeout=ClientTimeout(total=5), connector=connector) as session:
            async with session.get(QWEN_URL + "/v1/models") as resp:
                data = await resp.json()
                for m in data.get("data", []):
                    models.append(m)
        await connector.close()
    except Exception:
        models.append({"id": QWEN_MODEL, "object": "model", "owned_by": "local"})
    return web.json_response({"object": "list", "data": models})


async def health_handler(request: web.Request) -> web.Response:
    """Detailed health check of both backends."""
    health = {
        "status": "ok",
        "router": "hybrid-deepseek-qwen-v2",
        "backends": {},
    }

    # Check Qwen
    try:
        connector = make_connector(False)
        async with ClientSession(timeout=ClientTimeout(total=5), connector=connector) as session:
            async with session.get(QWEN_URL + "/health") as resp:
                health["backends"]["qwen"] = {"status": "ok" if resp.status == 200 else "degraded", "url": QWEN_URL}
        await connector.close()
    except Exception as e:
        health["backends"]["qwen"] = {"status": "down", "error": str(e), "url": QWEN_URL}
        health["status"] = "degraded"

    # Check DeepSeek
    health["backends"]["deepseek"] = {
        "status": "ok" if _deepseek_ok else "backoff",
        "fail_count": _deepseek_fail_count,
        "url": DEEPSEEK_URL,
    }
    if not _deepseek_ok:
        health["status"] = "degraded"

    return web.json_response(health)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/v1/models", models_handler)
    app.router.add_route("*", "/v1/{path:.*}", proxy_handler)
    app.router.add_route("*", "/{path:.*}", proxy_handler)
    return app


if __name__ == "__main__":
    if not DEEPSEEK_KEY:
        log.error("DEEPSEEK_API_KEY not set!")
        sys.exit(1)
    log.info("LLM Router v2 starting on :%d", LISTEN_PORT)
    log.info("  Qwen local  → %s (model: %s)", QWEN_URL, QWEN_MODEL)
    log.info("  DeepSeek    → %s (with fallback to Qwen)", DEEPSEEK_URL)
    web.run_app(create_app(), port=LISTEN_PORT, print=None)
