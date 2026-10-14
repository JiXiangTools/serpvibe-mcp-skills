# Browser Environment Manager Usage

## Address And Authentication

Commands below run from the skill directory. Otherwise use the absolute path to
`scripts/browser_env_manager.py`.

The service origin is selected in this order:

1. `--origin` before the subcommand;
2. `BROWSER_ENV_MANAGER_URL`;
3. `http://127.0.0.1:6001`.

The value must be an HTTP(S) origin without credentials, query, fragment, or a
path other than `/`.

```bash
python scripts/browser_env_manager.py --origin http://127.0.0.1:6001 ready
```

The helper reads `BROWSER_ENV_MANAGER_TOKEN`, then
`browser_env_manager__api_token`. Empty values omit control-plane
authentication. The shared default CDP uses this same optional Bearer header;
non-default CDP uses the ticket returned in its connection grant. Keep tokens,
tickets, and grant content out of arguments, URLs, logs, and chat.

## CLI

Prefix each subcommand with `python scripts/browser_env_manager.py`.

| Command | Purpose |
| --- | --- |
| `list` | List environments |
| `acquire [options]` | Acquire a connection and create a private grant file |
| `restart --grant-file <path>` | Restart a persistent environment's browser and replace its grant |
| `rotate --grant-file <path>` | Rotate a proxied environment and replace its grant |

Default browser tasks connect to the fixed shared CDP URL below. Named,
temporary, and proxy-backed tasks use `acquire` and the returned CDP connection.
Lease maintenance is automatic; do not add `release` or DELETE as a task-ending step.
Management commands are documented in [administration.md](administration.md).

`acquire` options:

| Option | Meaning |
| --- | --- |
| `--key <key>` | Persistent non-default environment key |
| `--temporary` | Disposable environment; mutually exclusive with `--key` |
| `--keep-open` | Create a persistent everyday browser; incompatible with `--temporary` |
| `--client-name <name>` | Printable owner label, at most 128 characters |
| `--proxy-provider commercial\|self_hosted` | Proxy provider intent |
| `--proxy-egress-ip <IP>` | Require this public IP for the acquisition |
| `--grant-file <path>` | New file for the grant; otherwise use a private temporary file |
| `--retry-attempts <1-8>` | Compatibility option for service-declared retryable errors; default 5 |

Without `--client-name`, the helper uses
`BROWSER_ENV_MANAGER_CLIENT_NAME`, then a process-based name. Grant files are
created with mode `0600`. `restart` and `rotate` atomically replace the supplied
grant file. Use the same origin for all operations; a grant does not store the
helper's control-plane origin.

## Environment Selection

- `default` is not acquired; connect to its stable shared gateway.
- `acquire --key <key>` gets or creates a persistent named environment.
- `acquire --temporary` creates a disposable environment.
- `acquire --proxy-provider <provider>` uses that provider's stable default key.
- Each non-default caller acquires a separate lease, even when callers share an environment.

Keys must match `[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}`. Email addresses are valid
logical keys. A new named environment without `--proxy-provider` is direct; an
existing environment reuses its stored provider policy.

For everyday use, create a named browser with `--keep-open`, optionally together
with `--proxy-provider commercial` or `self_hosted`. It stays open without a CDP
connection. Manual close still stops it, and a later acquire reopens the same
profile. This does not enable OS startup or automatic relaunch after closing.

The mode is saved when the environment is created. Omit the option when reusing
it; an explicit conflicting `keep_open` value returns `409 lifecycle_policy_mismatch`.
Change an existing environment through `configure` or PATCH, documented in
[administration.md](administration.md). Acquire never edits saved configuration.
The default for new named environments is false. Existing environments retain their
saved mode when the field is omitted or null. Normal capacity limits still apply.

## Shared Default CDP

The default gateway is stable and service-owned:

```text
ws://127.0.0.1:6001/browser-env-manager/api/v1/environments/default/cdp
```

For another service origin, preserve its host/port and map `http -> ws` or
`https -> wss`. The WebSocket handshake lazily creates or starts `default`,
keeps it configured as direct and always-on, and attaches every caller to the
same Chrome. It creates no connection lease, grant file, ticket, renewal, or
release obligation. The service closes an idle socket without closing Chrome.

When API authentication is enabled, pass the token only as an Authorization
header. This example requires `websockets>=15,<16`:

```python
import asyncio
import json
import os

from websockets.asyncio.client import connect

url = "ws://127.0.0.1:6001/browser-env-manager/api/v1/environments/default/cdp"
token = os.environ.get("BROWSER_ENV_MANAGER_TOKEN") or os.environ.get(
    "browser_env_manager__api_token"
)
headers = {"Authorization": f"Bearer {token.strip()}"} if token and token.strip() else None

async def get_targets():
    async with connect(url, additional_headers=headers, origin=None) as cdp:
        await cdp.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
        while True:
            message = json.loads(await asyncio.wait_for(cdp.recv(), timeout=10))
            if message.get("id") == 1:
                return message["result"]["targetInfos"]

targets = asyncio.run(get_targets())
```

Multiple programs may connect concurrently. Each should create or select its
own target/window and keep its work inside the WebSocket context manager.

## Non-Default Connection Grant And CDP

The helper prints non-secret metadata and the path of the grant file. The full
grant has this shape:

```json
{
  "lease_id": "<lease-id>",
  "client_name": "my-task",
  "state": "waiting",
  "created_at": "<timestamp>",
  "last_activity_at": "<timestamp>",
  "environment": {
    "environment_key": "account@example.com",
    "browser_environment_ref": "<opaque-ref>",
    "temporary": false,
    "configuration": {"keep_open": false, "proxy_provider": null},
    "runtime_state": "ready",
    "keep_open": false,
    "status": "active",
    "revision": 1,
    "browser_visual_mode": "visible",
    "browser_runtime_profile": "native",
    "browser_identity_assurance": "native",
    "proxy_provider": null,
    "last_egress_ip": null,
    "egress_generation": null,
    "created_at": "<timestamp>"
  },
  "websocket_url": "ws://<host>/browser-env-manager/api/v1/cdp/<lease-id>",
  "websocket_headers": {
    "X-Browser-Connection-Ticket": "<secret>"
  },
  "expires_at": "<timestamp>",
  "release_url": "http://<host>/browser-env-manager/api/v1/connections/<lease-id>",
  "browser_restart_url": "http://<host>/browser-env-manager/api/v1/connections/<lease-id>/browser-restarts",
  "proxy_rotation_url": null
}
```

Temporary grants have no restart or rotation URL. Persistent direct grants have
no rotation URL. Persistent proxied grants provide both action URLs.

Connect using the URL and all headers exactly as returned. This example requires
`websockets>=15,<16`:

```python
import asyncio
import json
from pathlib import Path

from websockets.asyncio.client import connect

grant = json.loads(Path("/private/grant.json").read_text())

async def get_targets():
    async with connect(
        grant["websocket_url"],
        additional_headers=grant["websocket_headers"],
        origin=None,
    ) as cdp:
        await cdp.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
        while True:
            message = json.loads(await asyncio.wait_for(cdp.recv(), timeout=10))
            if message.get("id") == 1:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message["result"]["targetInfos"]

targets = asyncio.run(get_targets())
```

Inspect existing targets before choosing one. To create a page, call
`Target.createTarget`; attach with `Target.attachToTarget` and `flatten: true`,
then include the returned `sessionId` in page-level commands. Match command
responses by `id` while processing CDP events independently.

Keep the browser operation inside `async with connect(...)`; the connection
context manager also exits on exceptions. No additional cleanup script is needed.

## Direct HTTP API

Base path: `<origin>/browser-env-manager/api/v1`. Add
`Authorization: Bearer <token>` only when configured.

| Method | Path | Purpose |
| --- | --- | --- |
| WS | `/environments/default/cdp` | Shared default CDP; optional Bearer auth, no lease/ticket |
| POST | `/connections` | Acquire a non-default connection; returns HTTP 201 and a grant |
| GET | `/environments` | List environments |
| POST | `/connections/{lease_id}/browser-restarts` | Restart browser; no request body |
| POST | `/connections/{lease_id}/proxy-rotations` | Rotate proxy; no request body |
| WS | `/cdp/{lease_id}` | CDP using `X-Browser-Connection-Ticket` |

Acquisition accepts:

```json
{
  "environment_key": "account@example.com",
  "temporary": false,
  "keep_open": true,
  "client_name": "my-task",
  "proxy_provider": "commercial",
  "proxy_egress_ip": "203.0.113.10"
}
```

All fields are optional, subject to these combinations:

- omitting all environment selection fields, or setting `environment_key` to
  `default`, returns `409 default_connection_uses_shared_gateway`;
- `environment_key` and `temporary: true` are mutually exclusive;
- `keep_open: true` requires a persistent environment (`temporary` omitted or false);
- `proxy_provider` is `commercial` or `self_hosted`;
- a new environment using `proxy_egress_ip` also supplies `proxy_provider`;
- an existing proxied environment can derive the provider from its key.

Restart and rotation require a persistent environment; rotation also requires
a proxy. After success, reload the replaced grant, establish a new CDP
connection, and rediscover target/session IDs. If the service returns
`environment_shared`, the environment is still in use and was not changed.
Do not release other callers' connections to make the operation succeed.

## Errors And Discovery

HTTP errors use:

```json
{"detail":{"code":"<code>","message":"<message>","retryable":false}}
```

| Status | Meaning |
| --- | --- |
| 401 | The configured token is missing or invalid |
| 404 | The requested environment, lease, or ticket does not exist |
| 409 | The operation conflicts with current environment state |
| 422 | Request fields are invalid |
| 429 | A connection limit was reached |
| 503 | A dependency or operation is temporarily unavailable |

The service handles startup recovery. A failed restart or rotation with
`retryable: false` ends that operation; report the error instead of adding a
release/reacquire recovery sequence. Readiness is `<origin>/ready`; OpenAPI is
`<origin>/browser-env-manager/openapi.json`; Swagger is
`<origin>/browser-env-manager/docs`.
