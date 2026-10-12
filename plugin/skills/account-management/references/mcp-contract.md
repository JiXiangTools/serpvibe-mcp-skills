# Browser operations

Use `account_browser`; exact fields are in the live schema or [tool-contract.json](tool-contract.json).

1. Start with `start_registration` and the exact registration URL, `start_login`
   for an `account_ref`, or `start_password_change` for an `account_ref` and its
   current revision. Supply a unique `request_id`; reuse it only for an identical
   start retry. Registration and password change generate the password for you.
2. Use the returned `operation_ref` for subsequent calls. Call `observe` for the
   page and use only `element_ref` values from the latest snapshot.
3. Call `navigate` with `url`, `click` with `element_ref`, `fill` with
   `element_ref` and `text`, or `select` with `element_ref` and `value`.
   These are top-level actions, not `act` or `command`. Each needs a
   session-unique `action_id`, reused only for the identical retry.
4. Use `inject_credentials` with the matching username/password element refs.
   Never `fill` a password field. The tool takes and returns no plaintext password.
5. Call `complete` only after visible site success; this saves the registered or
   changed credential. If the result is ambiguous, keep or cancel the operation
   and report the uncertainty. On `reconciliation_required`, re-read the account
   and retry `complete` with its current `expected_revision`; do not generate
   another password.

Use `resume` with `operation_ref` for a lost session; inspect the page before
repeating an external action. Use `cancel` to close the operation and clear an
uncommitted generated credential. These calls do not take a new `request_id`.

Keep page paths and query case intact. Navigation must stay on the account's
normalized host. Navigation, form actions, injection, and completion may change
the external site; never bypass CAPTCHA, email/device verification, or required
user confirmation.
