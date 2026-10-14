---
name: browser-env-manager
description: Connect to the shared default Chrome or acquire named, temporary, and proxy-backed Chrome environments through the Browser Environment Manager HTTP/CDP service. Use for browser sessions, environment discovery, browser restarts, proxy rotation, and cleanup.
---

# Browser Environment Manager

Use the bundled client. Paths below are relative to this skill directory; from
another working directory, use the script's absolute path.

## Start the Local Service

Before local browser work, ensure the service is ready with this idempotent command
(it can be called from any directory):

```bash
/Users/caturbhuja/PycharmProjects/browser-env-manager/deploy/start.sh --json
```

It starts the macOS background service on port 6001 or reuses it, waits for
readiness, and exits `0` with JSON `status: started|already_running` and `pid`.
Repeated or concurrent calls reuse the same service. Other programs can invoke
this script directly; no terminal session needs to stay open. See
[administration.md](references/administration.md) for timeout, errors and a Python
example. This starts the local service; a remote origin is managed on its host.

## Standard Use

1. For the shared local `default`, connect directly to the stable managed gateway:

   ```text
   ws://127.0.0.1:6001/browser-env-manager/api/v1/environments/default/cdp
   ```

   Do not call `acquire` for `default`. It has no caller-owned lease, ticket,
   renewal, or release step. Multiple clients may connect concurrently. When
   `browser_env_manager__api_token` is non-empty, send it as
   `Authorization: Bearer <token>` in the WebSocket handshake; otherwise send
   no authentication header.
2. For a named, temporary, or proxy-backed environment, acquire one connection:

   ```bash
   python scripts/browser_env_manager.py acquire --key account@example.com --client-name my-task
   python scripts/browser_env_manager.py acquire --temporary
   python scripts/browser_env_manager.py acquire --key daily-commercial --proxy-provider commercial --keep-open
   ```

   The helper defaults to `http://127.0.0.1:6001` and prints the path of a
   private grant file.
3. Read that grant, then connect to its `websocket_url` with every entry in
   `websocket_headers`. Perform browser work inside the CDP client's connection
   context manager (see the example in [api.md](references/api.md)). No separate
   lease maintenance or release command is part of normal browser work.

For daily browsers, use saved configuration and name-based operations:

```bash
python scripts/browser_env_manager.py create daily --proxy-provider commercial --keep-open
python scripts/browser_env_manager.py start daily
python scripts/browser_env_manager.py configure daily --no-keep-open
python scripts/browser_env_manager.py show daily
```

Creation saves a stopped environment. Later start/acquire uses its saved
configuration. `configure` changes only supplied fields; `--direct` clears the
proxy. See [administration.md](references/administration.md) for all operations.

## Other Browser Intents

```bash
python scripts/browser_env_manager.py list
python scripts/browser_env_manager.py restart --grant-file <path>
python scripts/browser_env_manager.py rotate --grant-file <path>
python scripts/browser_env_manager.py restart --key daily
python scripts/browser_env_manager.py rotate --key daily
python scripts/browser_env_manager.py stop daily
```

Use `restart` only for a browser restart intent and `rotate` only for an IP
replacement intent. With `--grant-file`, reload the replaced grant and connect
using its new headers. With `--key`, no CDP connection is required or issued.
Browser tasks do not call Proxy Manager separately.

Every non-default caller acquires its own connection; default callers share the
stable service gateway. Always use the service-provided CDP endpoint rather than
launching another Chrome. Never expose grant files, tokens, or tickets in URLs,
logs, command arguments, or chat. Delete a named environment only when the user
explicitly requests deletion.

Read [api.md](references/api.md) for connection options, request/response fields,
direct HTTP/CDP integration, and errors. For proxy acquisition or rotation, also
read [proxy-boundary.md](references/proxy-boundary.md). Read
[administration.md](references/administration.md) only for an explicit service
administration, connection revocation, or environment deletion task.
