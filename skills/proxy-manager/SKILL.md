---
name: proxy-manager
description: Acquire and manage HTTP proxy leases from the dedicated LAN Proxy Manager service. Use whenever a task needs a proxy, category selection, stable egress, lease release, or proxy failure reporting; never source proxies directly from pz-proxies or another project's local state.
---

# Proxy Manager

Use this service as the single proxy source. Do not inspect its SQLite inventory, call
`pz_proxies` directly, reuse another project's proxy state, or invent another proxy-selection
path. Treat it as a trusted-LAN service; never expose it to the public internet.

## Resolve the service

Use the base URL in this order:

1. A URL explicitly supplied by the user.
2. `PROXY_MANAGER_URL` when it is set.
3. `http://127.0.0.1:8000` only when running on the Proxy Manager host.

Normalize the selected base URL by removing a trailing slash. For a remote caller with no
configured URL, ask for the service's LAN DNS name or IP. Do not guess one. Check `GET /ready`
before starting a proxy-dependent workflow, and query `GET /api/v1/proxies/categories` instead
of hardcoding available categories.

## Acquire a proxy

Choose a stable, namespaced requirement such as `<project>:<workflow>:<worker-or-attempt>`.
Reuse it when the same logical consumer should recover the same lease.

- Use `long_lived` for a persistent consumer identity. Release it only when that ownership ends.
- Use `short_lived` for one task or attempt. Release it in cleanup even when the task fails.

```bash
curl -fsS -X POST "${PROXY_MANAGER_URL}/api/v1/proxies/acquire" \
  -H 'Content-Type: application/json' \
  -d '{"requirement":"research:crawl:attempt-42","category":"internal","lease_kind":"short_lived"}'
```

Consume the returned `proxy.url` exactly as provided. It is an HTTP proxy and supports HTTPS
through CONNECT. Keep `lease_ref`, `proxy_ref`, and `egress_generation` with the task result;
they identify the precise egress generation for failure reporting.

For example:

```bash
curl --proxy "$PROXY_URL" -fsS https://api.ipify.org/
```

With HTTPX, pass the returned URL as `proxy=proxy_url`. Do not replace its host with a loopback
address or expose the package-owned `127.0.0.1:18000-21999` endpoint.

## Release or report failure

Release by sending the exact same acquisition identity:

```bash
curl -fsS -X POST "${PROXY_MANAGER_URL}/api/v1/proxies/release" \
  -H 'Content-Type: application/json' \
  -d '{"requirement":"research:crawl:attempt-42","category":"internal","lease_kind":"short_lived"}'
```

For rate limiting or an egress failure, report facts from the acquire response:

```bash
curl -fsS -X POST "${PROXY_MANAGER_URL}/api/v1/proxies/report-failure" \
  -H 'Content-Type: application/json' \
  -d '{"lease_ref":"...","proxy_ref":"...","egress_generation":1,"kind":"rate_limited"}'
```

Allowed failure kinds are `rate_limited` and `egress_failure`. After an accepted report,
acquire again with the same requirement so the service can select the current usable egress.
For retryable `503` responses, honor `retry_at` when present and keep ordinary retries bounded.
Do not switch to a direct package call or another project's proxy state when the service is
unavailable.

## Operational boundary

Use read-only checks first when the current task also covers operation of the service host:

```bash
systemctl is-active proxy-manager.service
curl -fsS http://127.0.0.1:8000/ready
journalctl -u proxy-manager.service -n 100 --no-pager
```

Do not restart, stop, reconfigure, import inventory, or report a proxy failure unless the current
request authorizes that mutation. A normal proxy consumer should report service unavailability
instead of changing the host.
