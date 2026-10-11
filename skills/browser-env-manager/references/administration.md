# Service Administration

Use these commands only for an explicit administration task. Normal browser
work uses `acquire` and CDP as described in [api.md](api.md).

Prefix commands with `python scripts/browser_env_manager.py` from the skill
directory. Address and authentication options are the same as in api.md.

| Command | Purpose |
| --- | --- |
| `ready` | Check service readiness |
| `create <key> [--keep-open] [--proxy-provider commercial\|self_hosted]` | Save a new stopped persistent environment |
| `show <key>` | Read saved configuration and runtime state |
| `configure <key> [--keep-open\|--no-keep-open] [--proxy-provider commercial\|self_hosted\|--direct]` | Update only supplied configuration fields |
| `start <key>` | Start by saved configuration; reuse if already running |
| `stop <key>` | Normally close the browser, preserving configuration and profile |
| `restart --key <key>` | Restart without requiring a CDP grant |
| `rotate --key <key>` | Replace proxy IP and start without requiring a CDP grant |
| `connections` | List sanitized connection IDs, owners, state, and timestamps |
| `release --grant-file <path>` | Immediately revoke that connection and remove its grant file |
| `release --lease-id <id>` | Immediately revoke that connection without a grant file |
| `delete <key>` | Delete the environment and its stored state |

Delete an environment only when explicitly requested. Connection revocation
does not delete a persistent environment or its saved login state.

Management HTTP paths use `<origin>/browser-env-manager/api/v1`:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/connections` | List sanitized connection summaries; no tickets or internal CDP URLs |
| POST | `/environments` | Create with `environment_key` and optional `keep_open`, `proxy_provider`; HTTP 201 |
| GET | `/environments/{environment_key}` | Read configuration and runtime state |
| PATCH | `/environments/{environment_key}` | Change `keep_open` and/or `proxy_provider` |
| POST | `/environments/{environment_key}/start` | Start an existing environment |
| POST | `/environments/{environment_key}/stop` | Stop its browser |
| POST | `/environments/{environment_key}/restart` | Restart its browser |
| POST | `/environments/{environment_key}/rotate-proxy` | Replace its IP and start its browser |
| DELETE | `/connections/{lease_id}` | Revoke a connection; HTTP 200 with `released: false` if absent |
| DELETE | `/environments/{environment_key}` | Delete the environment, including its connections and stored state |

Create and PATCH use flat JSON fields, for example
`{"environment_key":"daily","keep_open":true,"proxy_provider":"commercial"}`
for creation and `{"proxy_provider":null}` to switch an existing environment
to direct access. Omitted PATCH fields retain their values; `keep_open:null`
is invalid. Unknown fields are rejected. An existing key returns 409 on create;
start never creates a missing key. Named management operations require a
persistent environment. Temporary sessions still use acquire.

Responses include `configuration: {keep_open, proxy_provider}` and
`runtime_state: stopped|starting|ready|stopping`. The older flat configuration
fields remain compatible projections. `keep_open` changes apply without
restarting; a proxy change restarts a running browser and preserves its profile.
A stopped browser remains stopped after configuration changes. A busy shared
environment returns `environment_shared` without changing it. Errors from
environment operations include `detail.environment` with the saved configuration
and current state; the helper prints it. A failed startup can leave the new
configuration saved with the browser stopped.

Create/show/configure/start/stop/key-based restart and rotation do not issue a
CDP grant. Use acquire when a CDP connection is wanted. Existing grant-based
restart/rotation remain supported. No rename, renew, arbitrary Chrome-argument,
or HTTP page-action endpoint is provided.

## Local Service Startup

Use the project's executable deployment script, including from other programs:

```python
import json
import subprocess

result = subprocess.run(
    ["/Users/caturbhuja/PycharmProjects/browser-env-manager/deploy/start.sh", "--json"],
    check=True, capture_output=True, text=True, timeout=130,
)
service = json.loads(result.stdout)
```

The command accepts `--timeout SECONDS` (default 120, including lock wait,
dependency sync and readiness). Start and stop serialize internally. Successful
start/reuse exits `0` with `status: started|already_running`, `pid`, `ready_url`,
`environment`, `label`, `stdout_log` and `stderr_log`. With `--json`, stdout is one
JSON object and progress goes to stderr. Operational failure exits `1` with
`status: error` and `error`; invalid CLI arguments exit `2`. A timeout leaves an
already submitted service available for the next call to check and reuse.

Defaults are `PZ_ENV=develop`, `APP_HOST=127.0.0.1`, `APP_PORT=6001`.
Use `PZ_ENV` to select `develop|test|product`; host/port overrides are forwarded
to PZ. Changing these while a service is registered requires an explicit stop.
`BROWSER_ENV_MANAGER_READY_URL` changes only the readiness probe URL.
The script requires a logged-in macOS user session, Python 3 and uv. An existing
ready service does not require another dependency sync. A foreign LaunchAgent
or an unmanaged listener is reported as an error and left untouched.

`/Users/caturbhuja/PycharmProjects/browser-env-manager/deploy/stop.sh --json`
stops the service on explicit request (`stopped|already_stopped`), preserving
browser environments. Logs are in the project's `.runtime/deploy/`.
Readiness is `<origin>/ready`; OpenAPI is
`<origin>/browser-env-manager/openapi.json`; Swagger is `<origin>/browser-env-manager/docs`.
