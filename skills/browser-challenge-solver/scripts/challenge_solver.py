#!/usr/bin/env python3
"""Pass an existing managed tab to Browser Challenge Solver without exposing secrets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class ClientError(Exception):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A redirected request must never forward a CDP ticket to a different service.
        return None


def origin(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ClientError("invalid service origin") from None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or (port is not None and port < 1)
    ):
        raise ClientError("service origin must be HTTP(S) without credentials or a path")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def read_private_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ClientError("private JSON input must be an object")
        return value
    except (OSError, ValueError):
        raise ClientError("cannot read private JSON input file") from None


def connection(args) -> dict:
    if args.grant_file:
        grant = read_private_json(args.grant_file)
        url, headers = grant.get("websocket_url"), grant.get("websocket_headers")
        if not isinstance(url, str) or not isinstance(headers, dict):
            raise ClientError("grant requires websocket_url and websocket_headers")
        return {"websocket_url": url, "websocket_headers": headers}
    manager = urlsplit(
        origin(
            args.browser_origin or os.getenv("BROWSER_ENV_MANAGER_URL") or "http://127.0.0.1:6001"
        )
    )
    endpoint = urlunsplit(
        (
            "wss" if manager.scheme == "https" else "ws",
            manager.netloc,
            "/browser-env-manager/api/v1/environments/default/cdp",
            "",
            "",
        )
    )
    token = (
        os.getenv("BROWSER_ENV_MANAGER_TOKEN") or os.getenv("browser_env_manager__api_token") or ""
    ).strip()
    return {
        "websocket_url": endpoint,
        "websocket_headers": {"Authorization": f"Bearer {token}"} if token else {},
    }


def send(service_origin: str, path: str, *, payload: dict | None = None, timeout: int = 30) -> dict:
    headers = {"Accept": "application/json"}
    token = os.getenv("CHALLENGE_SOLVER_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        service_origin + path,
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    try:
        with build_opener(ProxyHandler({}), NoRedirects()).open(
            request, timeout=timeout
        ) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ClientError("invalid service response; do not automatically repeat a solve")
        return result
    except HTTPError as error:
        raise ClientError(f"service returned HTTP {error.code}") from None
    except (URLError, OSError, ValueError):
        raise ClientError("service request failed; do not automatically repeat a solve") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", help="Challenge Solver HTTP(S) origin")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ready")
    solve = commands.add_parser("solve")
    selection = solve.add_mutually_exclusive_group(required=True)
    selection.add_argument("--grant-file", type=Path)
    selection.add_argument("--shared-default", action="store_true")
    solve.add_argument(
        "--browser-origin", help="Browser Environment Manager origin, for shared default"
    )
    solve.add_argument("--target-id", required=True)
    solve.add_argument("--provider", choices=("auto", "capsolver", "2captcha"), default="auto")
    solve.add_argument(
        "--challenge-kind",
        default="auto",
        choices=(
            "auto",
            "recaptcha_v2",
            "recaptcha_v2_enterprise",
            "hcaptcha",
            "turnstile",
            "cloudflare_interstitial",
            "image_captcha",
        ),
    )
    solve.add_argument("--timeout-seconds", type=int, default=300)
    for name in ("widget", "image", "response", "success"):
        solve.add_argument(f"--{name}-selector")
    solve.add_argument("--proxy-file", type=Path)
    solve.add_argument("--reload-safe", action="store_true")
    args = parser.parse_args(argv)
    try:
        service_origin = origin(
            args.origin or os.getenv("CHALLENGE_SOLVER_URL") or "http://127.0.0.1:6002"
        )
        if args.command == "ready":
            print(json.dumps(send(service_origin, "/ready")))
            return 0
        if not 10 <= args.timeout_seconds <= 600:
            raise ClientError("timeout-seconds must be between 10 and 600")
        if args.grant_file and args.browser_origin:
            raise ClientError("browser-origin applies only to shared-default")
        payload = {
            "cdp": connection(args),
            "target_id": args.target_id,
            "provider": args.provider,
            "challenge_kind": args.challenge_kind,
            "timeout_seconds": args.timeout_seconds,
            "reload_safe": args.reload_safe,
        }
        for name in ("widget_selector", "image_selector", "response_selector", "success_selector"):
            value = getattr(args, name)
            if value:
                payload[name] = value
        if args.proxy_file:
            proxy = read_private_json(args.proxy_file).get("proxy_url")
            if not isinstance(proxy, str):
                raise ClientError("proxy file requires proxy_url")
            payload["proxy_url"] = proxy
        result = send(
            service_origin,
            "/browser-challenge-solver/api/v1/solve",
            payload=payload,
            timeout=args.timeout_seconds + 15,
        )
        public = {
            key: result[key]
            for key in (
                "status",
                "reason",
                "target_id",
                "challenge_kind",
                "provider",
                "provider_task_id",
                "token_applied",
                "verified",
                "elapsed_ms",
            )
            if key in result
        }
        print(json.dumps(public, ensure_ascii=False))
        if result.get("status") in {"solved", "token_applied"}:
            return 0
        return 3 if result.get("status") == "timeout" else 2
    except ClientError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
