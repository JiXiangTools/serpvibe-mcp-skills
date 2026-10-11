#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

DEFAULT_ORIGIN = "http://127.0.0.1:6001"
MOUNT_PATH = "/browser-env-manager"


class ClientError(RuntimeError):
    pass


class ClientHttpError(ClientError):
    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        code: str | None = None,
        retryable: bool = False,
        environment: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.code = code
        self.retryable = retryable
        self.environment = environment


def _origin(value: str | None) -> str:
    raw = str(value or os.environ.get("BROWSER_ENV_MANAGER_URL") or DEFAULT_ORIGIN)
    parsed = urlsplit(raw.strip())
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ClientError("BROWSER_ENV_MANAGER_URL must be an http(s) origin")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _token() -> str | None:
    value = (
        os.environ.get("BROWSER_ENV_MANAGER_TOKEN")
        or os.environ.get("browser_env_manager__api_token")
        or ""
    ).strip()
    return value or None


def _request(
    origin: str,
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    token = _token()
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    url = (
        f"{origin}{MOUNT_PATH}{path}"
        if path.startswith("/api/")
        else f"{origin}{path}"
    )
    request = Request(url, data=data, headers=headers, method=method)
    try:
        # Browser startup and service-owned recovery can outlast a read request.
        # A premature timeout leaves an operation running without its grant.
        with urlopen(request, timeout=600 if method in {"POST", "PATCH", "DELETE"} else 30) as response:
            body = response.read()
    except HTTPError as exc:
        body = exc.read()
        code = None
        retryable = False
        environment = None
        try:
            detail = json.loads(body).get("detail", {})
            message = detail.get("message") or detail.get("code")
            code = detail.get("code")
            retryable = detail.get("retryable") is True
            environment = detail.get("environment")
        except (AttributeError, json.JSONDecodeError):
            message = None
        raise ClientHttpError(
            exc.code,
            str(message or exc.reason),
            code=str(code) if code is not None else None,
            retryable=retryable,
            environment=environment if isinstance(environment, dict) else None,
        ) from exc
    except URLError as exc:
        raise ClientError(f"service request failed: {exc.reason}") from exc
    if not body:
        return {}
    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ClientError("service returned non-JSON data") from exc
    if not isinstance(result, dict):
        raise ClientError("service returned an unexpected response")
    return result


def _request_with_retry(
    origin: str,
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    attempts: int = 5,
) -> dict[str, Any]:
    for attempt in range(attempts):
        try:
            return _request(origin, method, path, payload=payload)
        except ClientHttpError as exc:
            if not exc.retryable or attempt + 1 >= attempts:
                raise
            time.sleep(min(0.1 * (2**attempt), 1.0))
    raise AssertionError("bounded request loop did not return")


def _client_name(value: str | None) -> str:
    name = str(
        value
        or os.environ.get("BROWSER_ENV_MANAGER_CLIENT_NAME")
        or f"browser-env-client-{os.getpid()}"
    ).strip()
    if not name or len(name) > 128 or any(
        ord(character) < 32 or ord(character) == 127 for character in name
    ):
        raise ClientError("client name must be at most 128 printable characters")
    return name


def _write_private_grant(grant: dict[str, Any], requested: Path | None) -> Path:
    encoded = (json.dumps(grant, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if requested is None:
        descriptor, name = tempfile.mkstemp(
            prefix="browser-env-manager-grant-",
            suffix=".json",
        )
        path = Path(name)
    else:
        path = requested.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(encoded)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        path.unlink(missing_ok=True)
        raise
    return path


def _read_grant(path: Path) -> dict[str, Any]:
    try:
        grant = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError) as exc:
        raise ClientError("grant file does not contain a valid connection grant") from exc
    if not isinstance(grant, dict) or not str(grant.get("lease_id") or "").strip():
        raise ClientError("grant file is missing a valid lease_id")
    return grant


def _replace_private_grant(grant: dict[str, Any], path: Path) -> None:
    encoded = (json.dumps(grant, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(encoded)
        os.replace(temporary, path)
        path.chmod(0o600)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _acquire(args: argparse.Namespace, origin: str) -> None:
    if args.temporary and args.keep_open:
        raise ClientError("--keep-open requires a persistent environment")
    payload: dict[str, Any] = {"client_name": _client_name(args.client_name)}
    if args.keep_open is not None:
        payload["keep_open"] = args.keep_open
    if args.key is not None:
        payload["environment_key"] = args.key
    if args.temporary:
        payload["temporary"] = True
    if args.proxy_provider is not None:
        payload["proxy_provider"] = args.proxy_provider
    if args.proxy_egress_ip is not None:
        payload["proxy_egress_ip"] = args.proxy_egress_ip
    grant = _request_with_retry(
        origin,
        "POST",
        "/api/v1/connections",
        payload=payload,
        attempts=args.retry_attempts,
    )
    environment = grant.get("environment")
    if not isinstance(environment, dict):
        raise ClientError("connection response is missing the environment")
    grant_file = _write_private_grant(grant, args.grant_file)
    _print(
        {
            "browser_visual_mode": environment.get("browser_visual_mode"),
            "client_name": grant.get("client_name"),
            "environment_key": environment.get("environment_key"),
            "expires_at": grant.get("expires_at"),
            "grant_file": str(grant_file),
            "lease_id": grant.get("lease_id"),
            "proxy_provider": environment.get("proxy_provider"),
            "last_egress_ip": environment.get("last_egress_ip"),
            "temporary": environment.get("temporary"),
            "keep_open": environment.get("keep_open", False),
        }
    )


def _release(args: argparse.Namespace, origin: str) -> None:
    grant_file = args.grant_file.expanduser().resolve() if args.grant_file else None
    lease_id = args.lease_id
    if grant_file is not None:
        lease_id = _read_grant(grant_file)["lease_id"]
    try:
        result = _request(
            origin,
            "DELETE",
            f"/api/v1/connections/{quote(str(lease_id), safe='')}",
        )
    except ClientHttpError as exc:
        if exc.status_code != 404 or exc.code != "connection_not_found":
            raise
        result = {"lease_id": lease_id, "released": False, "already_absent": True}
    if grant_file is not None:
        grant_file.unlink(missing_ok=True)
    _print(result)


def _rotate(args: argparse.Namespace, origin: str) -> None:
    grant_file = args.grant_file.expanduser().resolve()
    grant = _read_grant(grant_file)
    lease_id = str(grant["lease_id"])
    replacement = _request(
        origin,
        "POST",
        f"/api/v1/connections/{quote(lease_id, safe='')}/proxy-rotations",
    )
    if replacement.get("lease_id") != lease_id:
        raise ClientError("rotation response changed the connection lease")
    if replacement.get("websocket_url") != grant.get("websocket_url"):
        raise ClientError("rotation response changed the stable CDP gateway URL")
    environment = replacement.get("environment")
    if not isinstance(environment, dict):
        raise ClientError("rotation response is missing the environment")
    _replace_private_grant(replacement, grant_file)
    _print(
        {
            "egress_generation": environment.get("egress_generation"),
            "environment_key": environment.get("environment_key"),
            "expires_at": replacement.get("expires_at"),
            "grant_file": str(grant_file),
            "last_egress_ip": environment.get("last_egress_ip"),
            "lease_id": lease_id,
            "proxy_provider": environment.get("proxy_provider"),
            "websocket_url_unchanged": True,
        }
    )


def _restart(args: argparse.Namespace, origin: str) -> None:
    grant_file = args.grant_file.expanduser().resolve()
    grant = _read_grant(grant_file)
    lease_id = str(grant["lease_id"])
    replacement = _request(
        origin,
        "POST",
        f"/api/v1/connections/{quote(lease_id, safe='')}/browser-restarts",
    )
    if replacement.get("lease_id") != lease_id:
        raise ClientError("restart response changed the connection lease")
    if replacement.get("websocket_url") != grant.get("websocket_url"):
        raise ClientError("restart response changed the stable CDP gateway URL")
    environment = replacement.get("environment")
    if not isinstance(environment, dict):
        raise ClientError("restart response is missing the environment")
    _replace_private_grant(replacement, grant_file)
    _print(
        {
            "environment_key": environment.get("environment_key"),
            "expires_at": replacement.get("expires_at"),
            "grant_file": str(grant_file),
            "lease_id": lease_id,
            "websocket_url_unchanged": True,
        }
    )


def _environment(args: argparse.Namespace, origin: str) -> None:
    path = f"/api/v1/environments/{quote(args.key, safe='')}"
    if args.command in {"create", "configure"}:
        payload = {}
        if args.keep_open is not None:
            payload["keep_open"] = args.keep_open
        if args.direct:
            payload["proxy_provider"] = None
        elif args.proxy_provider is not None:
            payload["proxy_provider"] = args.proxy_provider
        if args.command == "create":
            payload["environment_key"] = args.key
            _print(_request(origin, "POST", "/api/v1/environments", payload=payload))
        else:
            _print(_request(origin, "PATCH", path, payload=payload))
    elif args.command == "show":
        _print(_request(origin, "GET", path))
    else:
        action = "rotate-proxy" if args.command == "rotate" else args.command
        _print(_request(origin, "POST", f"{path}/{action}"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Control Browser Environment Manager without exposing secrets."
    )
    parser.add_argument("--origin", help="Override BROWSER_ENV_MANAGER_URL")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("ready", help="Check the PZ host readiness endpoint")

    acquire = commands.add_parser("acquire", help="Acquire a browser connection")
    mode = acquire.add_mutually_exclusive_group()
    mode.add_argument("--key", help="Stable persistent environment key")
    mode.add_argument("--temporary", action="store_true", help="Disposable environment")
    acquire.add_argument(
        "--keep-open", action="store_true", default=None,
        help="Create a persistent everyday browser that stays open without CDP clients",
    )
    acquire.add_argument(
        "--grant-file",
        type=Path,
        help="New private file for the full connection grant",
    )
    acquire.add_argument(
        "--client-name",
        help="Human-readable connection owner (defaults to process identity)",
    )
    acquire.add_argument(
        "--retry-attempts",
        type=int,
        choices=range(1, 9),
        default=5,
        metavar="1-8",
        help="Attempts for service-declared retryable acquisition failures",
    )
    acquire.add_argument(
        "--proxy-provider",
        choices=("commercial", "self_hosted"),
        help="Bind a new environment to a managed proxy provider",
    )
    acquire.add_argument(
        "--proxy-egress-ip",
        help="Require this public IP for the current acquisition",
    )

    commands.add_parser("list", help="List environments")
    commands.add_parser("connections", help="List active connection leases")

    for name in ("create", "configure"):
        environment = commands.add_parser(name, help="Save environment configuration" if name == "create" else "Update saved configuration")
        environment.add_argument("key")
        environment.add_argument("--keep-open", action=argparse.BooleanOptionalAction, default=None)
        proxy = environment.add_mutually_exclusive_group()
        proxy.add_argument("--proxy-provider", choices=("commercial", "self_hosted"))
        proxy.add_argument("--direct", action="store_true", help="Use direct access without a proxy")
    for name in ("show", "start", "stop"):
        environment = commands.add_parser(name, help=f"{name.title()} an existing environment")
        environment.add_argument("key")

    delete = commands.add_parser("delete", help="Delete a persistent environment")
    delete.add_argument("key")

    release = commands.add_parser("release", help="Release a connection")
    release_mode = release.add_mutually_exclusive_group(required=True)
    release_mode.add_argument("--lease-id")
    release_mode.add_argument("--grant-file", type=Path)

    restart = commands.add_parser(
        "restart",
        help="Restart the current browser and update an existing grant file",
    )
    restart_target = restart.add_mutually_exclusive_group(required=True)
    restart_target.add_argument("--grant-file", type=Path)
    restart_target.add_argument("--key")

    rotate = commands.add_parser(
        "rotate",
        help="Replace a failed proxy and update an existing grant file",
    )
    rotate_target = rotate.add_mutually_exclusive_group(required=True)
    rotate_target.add_argument("--grant-file", type=Path)
    rotate_target.add_argument("--key")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        origin = _origin(args.origin)
        if args.command == "ready":
            _request(origin, "GET", "/ready")
            _print({"origin": origin, "ready": True})
        elif args.command == "acquire":
            _acquire(args, origin)
        elif args.command == "list":
            _print(_request(origin, "GET", "/api/v1/environments"))
        elif args.command == "connections":
            _print(_request(origin, "GET", "/api/v1/connections"))
        elif args.command in {"create", "configure", "show", "start", "stop"} or (
            args.command in {"restart", "rotate"} and args.key is not None
        ):
            _environment(args, origin)
        elif args.command == "delete":
            _print(
                _request(
                    origin,
                    "DELETE",
                    f"/api/v1/environments/{quote(args.key, safe='')}",
                )
            )
        elif args.command == "release":
            _release(args, origin)
        elif args.command == "restart":
            _restart(args, origin)
        elif args.command == "rotate":
            _rotate(args, origin)
        else:
            raise ClientError(f"unsupported command: {args.command}")
    except ClientError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if isinstance(exc, ClientHttpError) and exc.environment is not None:
            _print({"environment": exc.environment})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
