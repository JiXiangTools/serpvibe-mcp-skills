---
name: browser-challenge-solver
description: Resolve a CAPTCHA or human verification challenge blocking an authorized browser task by handing the existing managed tab to Browser Challenge Solver. Use the current CDP connection and target ID; supports reCAPTCHA v2, Enterprise v2, hCaptcha, Turnstile, image text CAPTCHAs, and eligible Cloudflare challenge pages. Does not handle SMS, email codes, MFA, identity checks, or account recovery.
---

# Browser Challenge Solver

When a supported verification challenge blocks the current authorized task, use
this skill before asking the user to solve it manually. Work on the original
Browser Environment Manager tab, with the same connection grant and `target_id`.
Pause other automation on that tab until the solver returns.

The shared `default` gateway allows concurrent sockets, so its original control
connection can stay open. A named/temporary grant allows only one active socket:
first close the original automation's CDP socket, immediately hand its same grant
to the solver, and reconnect the original automation with that grant as soon as
the solver returns. Closing a socket preserves the tab and form; do not release
the grant, close Chrome, or acquire a replacement environment. The reconnect
window is bounded by the manager. If the controller cannot yield its socket,
report that handoff cannot start rather than forcibly interrupting another caller.

## Resolve the current challenge

For a named or temporary environment, pass the existing private grant file:

```bash
python3 scripts/challenge_solver.py solve --grant-file /private/connection.json --target-id PAGE_ID
```

For the shared `default` browser:

```bash
python3 scripts/challenge_solver.py solve --shared-default --target-id PAGE_ID
```

Paths are relative to this skill directory; use absolute script paths from
another working directory. The helper uses `CHALLENGE_SOLVER_URL`, defaulting to
`http://127.0.0.1:6002`. It reads `CHALLENGE_SOLVER_TOKEN` when configured. The
shared default uses `BROWSER_ENV_MANAGER_URL` (default `http://127.0.0.1:6001`)
and its usual optional Bearer token. A grant's URL and every returned WebSocket
header are forwarded without changing the connection or acquiring another lease.

The service owns provider keys; never put them into tool arguments or messages.
Do not print a grant, connection ticket, proxy password, CAPTCHA answer or token.

Supply a site-specific, visible success marker when available:

```bash
python3 scripts/challenge_solver.py solve --grant-file /private/connection.json --target-id PAGE_ID --success-selector '#verification-success'
```

For an image text CAPTCHA, inspect the page and identify the image and its answer
input. Only the image region is sent for recognition:

```bash
python3 scripts/challenge_solver.py solve --grant-file /private/connection.json --target-id PAGE_ID --image-selector '#captcha-image' --response-selector '#captcha-answer'
```

Use `--widget-selector` to select one widget when multiple challenges are present.
Use `--response-selector` only for the selected widget's actual response field.
Optional `--provider capsolver|2captcha` selects one service explicitly; automatic
selection uses configured providers supported for that challenge. A solve creates
at most one paid provider task. See [api.md](references/api.md) for all options.

## Continue from the result

- `solved`, `verified: true`: the supplied visible page success marker was observed.
  Resume the original task in the same tab.
- `token_applied`, `verified: false`: an answer or clearance was applied. Inspect
  the page, then perform the original task's already authorized continuation and
  verify its result. This is not proof that the website accepted the answer.
- `not_detected`: no supported challenge was found. Inspect the original tab;
  this is not proof that verification passed.
- `needs_human`, `failed`, or `timeout`: stop automatic solve attempts, report
  the reason, and preserve the tab and form for the user. A timed-out or uncertain
  submission may still have created a paid task; do not repeat it automatically.

The service never submits a business form or closes the tab. A site's CAPTCHA
callback may itself continue the current flow. Check the page before repeating
any original action after the solve. Do not repeat a purchase, publication,
message, registration or another external action merely to test the answer.

## Cloudflare challenge pages

Whole-page Cloudflare challenges require the exact same static/sticky proxy
already used by the browser and a matching supported User-Agent. If that proxy
is available in a private file `{"proxy_url":"http://user:password@host:port"}`,
pass `--proxy-file /private/original-proxy.json`. Never acquire a different proxy
or rotate the browser to make the solver work. Missing same-egress information
returns `same_egress_proxy_required`.

The solver preserves the document by default. Add `--reload-safe` only when the
target is a read-only, safe-to-reload challenge page; it permits one reload of
that same tab after applying clearance. Never use it for a form with unsent input
or a page reached through a state-changing submission.

The service keeps its CDP connection active while waiting for the provider.
Close only the solver's connection when it returns, then resume the original
connection as described above. Do not close the target, restart Chrome,
release its grant, change its IP, or open a replacement tab as solver cleanup.
SMS/email verification, MFA, identity checks and unsupported challenge types
remain with the original task or the user.
