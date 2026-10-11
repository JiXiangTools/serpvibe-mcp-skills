# Proxy Usage

## Acquire A Proxy Environment

| `proxy_provider` | Meaning | Default key without `--key` |
| --- | --- | --- |
| `commercial` | Purchased commercial proxy | `proxy-commercial` |
| `self_hosted` | Proxy on owned servers | `proxy-self-hosted` |

Examples from the skill directory:

```bash
python scripts/browser_env_manager.py acquire --proxy-provider commercial
python scripts/browser_env_manager.py acquire --key wiki --proxy-provider commercial
python scripts/browser_env_manager.py acquire --temporary --proxy-provider self_hosted
python scripts/browser_env_manager.py acquire --key wiki --proxy-egress-ip 203.0.113.10
python scripts/browser_env_manager.py acquire --key daily-commercial --proxy-provider commercial --keep-open
```

For direct HTTP, use the corresponding fields:

```json
{
  "environment_key": "wiki",
  "proxy_provider": "commercial",
  "proxy_egress_ip": "203.0.113.10"
}
```

Provider is saved when a named environment is created. Change it explicitly
through `configure <key> --proxy-provider ...` or PATCH; `--direct` removes it.
An existing proxy environment can omit `proxy_provider`; a new one cannot when it supplies
`proxy_egress_ip`. The egress IP constrains this acquisition only.
Different named environments have separate profiles and proxy assignments;
`--keep-open` does not guarantee distinct public IPs. Select a required IP using
`--proxy-egress-ip` when needed, subject to Proxy Manager availability.

## Rotate The Current Proxy

After the browser task determines that the current IP should be replaced:

```bash
python scripts/browser_env_manager.py rotate --grant-file <path>
```

Direct HTTP equivalent:

```http
POST /browser-env-manager/api/v1/connections/{lease_id}/proxy-rotations
```

The request has no body or provider field. Rotation requires a persistent proxy
environment. On success the helper replaces the grant file. Reload it, connect
with the new ticket, and rediscover target/session IDs. On failure, report the
returned error. Do not release other callers or add a lease recovery sequence.

Proxy Manager owns IP allocation and replacement. Browser tasks express their
proxy intent through Browser Environment Manager; they do not call proxy
acquire, failure-reporting, or release endpoints themselves.
