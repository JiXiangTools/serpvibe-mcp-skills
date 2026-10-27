# Browser Challenge Solver usage

The service must already be configured and running. Check it with:

```bash
python3 scripts/challenge_solver.py ready
```

`status: unconfigured` means no provider key is installed on the service. Report
this to the operator; do not search another project's configuration for secrets.

The helper's global `--origin` option takes precedence over `CHALLENGE_SOLVER_URL`,
then `http://127.0.0.1:6002`. `CHALLENGE_SOLVER_TOKEN` supplies optional Bearer
authentication. Use a trusted local/LAN service origin; connection grants grant
access to the existing browser environment.

## Solve options

| Option | Meaning |
| --- | --- |
| `--grant-file PATH` | Existing private manager grant; exclusive with `--shared-default` |
| `--shared-default` | Connect to the manager's shared default gateway |
| `--browser-origin ORIGIN` | Manager origin for the shared default only |
| `--target-id ID` | Required exact existing page target |
| `--provider auto\|capsolver\|2captcha` | Default `auto`; choose one configured supported provider |
| `--challenge-kind KIND` | Default `auto`; otherwise assert a supported type |
| `--timeout-seconds N` | Entire operation deadline, default 300, range 10–600 |
| `--widget-selector CSS` | Disambiguate the current widget |
| `--image-selector CSS` | Image text CAPTCHA region; requires response selector |
| `--response-selector CSS` | Actual CAPTCHA response field |
| `--success-selector CSS` | Visible site success marker used to verify acceptance |
| `--proxy-file PATH` | Private JSON containing the browser's original static/sticky `proxy_url` |
| `--reload-safe` | Permit one reload after applying Cloudflare whole-page clearance |

Supported explicit types: `recaptcha_v2`, `recaptcha_v2_enterprise`, `hcaptcha`,
`turnstile`, `cloudflare_interstitial`, `image_captcha`.

Only `solved` with `verified: true` proves the supplied page success marker was
observed. `token_applied` requires the original workflow to continue and inspect
the result. `not_detected` requires inspection. A failure preserves the page.

The CLI exits `0` for `solved` or `token_applied`, `3` for a solve timeout, `2`
for other solve outcomes, and `1` for an HTTP/client failure. Inspect the JSON
status, not just the exit code. It never automatically retries a solve.

The default gateway permits concurrent connections. A named/temporary grant
permits one active WebSocket: the original controller must close only its socket
before the solve and reconnect promptly with the same grant afterwards. The
solver sends read-only targeted activity while awaiting the provider. Never
release or replace the lease as a handoff step. An occupied or expired ticket
can fail the CDP handshake without changing the original tab.

## Direct HTTP call

`POST /browser-challenge-solver/api/v1/solve` accepts JSON with required
`cdp: {websocket_url, websocket_headers}` and `target_id`. Each solve option above
maps to its underscore-separated field (`timeout_seconds`, `widget_selector`,
etc.); `proxy_url` is read from the private proxy file. The response contains
`status`, `reason`, `target_id`, `challenge_kind`, `provider`, `provider_task_id`,
`token_applied`, `verified` and `elapsed_ms`. Answers and credentials stay inside
the service and page.

HTTP `401` means authentication failed, `409` means another request is already
solving that target, and `422` means an invalid request. A successfully processed
request returns HTTP `200` with one of the result statuses, including failure
outcomes. Do not repeat an uncertain HTTP submission automatically.
