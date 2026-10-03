# Website facts

The live MCP schema defines exact fields. Use these rules when deciding what belongs in a website record.

- `normalized_host` is site identity. Page path and query are not website identity; `www` is distinct unless stored as a verified alias.
- An alias needs verified evidence and a check time. A shared name or root domain is not enough.
- Exploration status is `unexplored`, `valid`, or `invalid`. `invalid` records useful negative knowledge and is not deletion.
- Quality needs a conclusion and check time. Traffic needs a metric, value, unit, source, and observation time. Evidence needs a kind, source URL, concise summary, and observation time.
- Store observed values only. A failed collection is not a traffic observation; full pages, browser state, credentials, and task history do not belong here.
- Tags are exact `dimension.value` codes. Only active definitions may be added; archived tags may remain or be removed.
- Projection changes only the response: `summary` is compact, `standard` adds working detail, and `full` adds traffic, evidence, and deletion fields.
