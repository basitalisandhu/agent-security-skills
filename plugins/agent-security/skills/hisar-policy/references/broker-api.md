# Hisar Broker: the shapes this skill relies on

Condensed from `docs/api-reference.md`, `docs/concepts.md` and `docs/agent-developer-guide.md` of https://basitalisandhu.github.io/hisar/hisar-broker.html. When in doubt, those documents win.

## Credentials

| Credential | Header | Used for |
|---|---|---|
| Admin token or operator token (`hop.op-<12 hex>.<32 chars>`) | `Authorization: Bearer <token>` on `/admin/api/*` | Creating connectors, agents, policies; approvals; audit |
| Agent key (`hsk.ag-<12 hex>.<32 chars>`), shown once | `X-Hisar-Agent-Key: <key>` on `/v1/whoami`, `/v1/token`, `/v1/requests/:id`, `/v1/events`, `/v1/lease` | Asking for tokens |
| Access token (ES256 JWT, minutes) | `Authorization: Bearer <token>` on `/v1/proxy/*` | Proxied upstream calls |

Operator roles: `admin` (everything), `approver` (`GET /me`, `/overview`, `/requests`, approve, deny), `auditor` (read lists, audit, evidence).

## Scopes

- 1 to 200 characters from `A-Z a-z 0-9 _ . : / * @ % ~ -`.
- `*` matches any run of characters, including none, including `/` and `:`. Everything else is literal and case-sensitive. The pattern must match the whole scope.
- Conventions: proxied call `connector:METHOD:/path` (METHOD upper case; path is what follows `/v1/proxy/<connector>`, decoded, without query); MCP tool via hisar-mcp `mcp:<server>:<tool>`; secret lease `lease:<connector>`; your own services: any string (`orders:read`).
- Trailing `*` is a prefix match: `crm:GET:/contacts*` also matches `/contacts-archive`. For a segment boundary use `crm:GET:/contacts` plus `crm:GET:/contacts/*`.

## Policies

| Field | Rule | Default |
|---|---|---|
| `scope_pattern` | scope pattern, up to 200 chars | required |
| `max_ttl` | integer seconds, 10 to 86400 | 300 |
| `requires_approval` | boolean; a human approves each token | false |
| `single_use` | boolean; the token is spent by its first proxied call | false |

- Policies only grant; there is no deny. No matching policy means `403 scope_not_allowed`.
- Most specific matching policy wins: longest literal part (pattern with `*` removed). Ties are not promised; avoid them.
- A wildcard request (`crm:*`) must be covered by some policy and inherits the strictest terms of every policy it overlaps: if any overlapping policy is gated, the request is gated; the shortest `max_ttl` applies.
- A `lease:` policy cannot require approval (`403 lease_cannot_be_approval_gated`).
- Up to 50 policies in one create-agent call; more via `POST /admin/api/agents/:id/policies`.
- Token TTL = min(requested ttl, policy max_ttl, HISAR_MAX_TTL). Approval re-checks current policies and applies the stricter of request-time and approval-time terms.

## Connectors

`POST /admin/api/connectors`

| Field | Rule |
|---|---|
| `name` | `^[a-z0-9][a-z0-9-]{1,39}$` |
| `base_url` | http or https; no credentials, query or fragment; private or local hosts refused unless `HISAR_ALLOW_PRIVATE_UPSTREAMS=1` |
| `auth_header` | header name, default `Authorization` |
| `auth_prefix` | up to 40 chars, default `Bearer ` |
| `secret` | 1 to 4000 chars; never returned |

Errors: `400 invalid_request`, `400 upstream_not_allowed`, `409 connector_exists`. `GET /admin/api/connectors` never returns secrets. `DELETE /admin/api/connectors/:id`.

## Agents

`POST /admin/api/agents` with `name` (1 to 120), optional `owner` (120), `description` (1000), `policies` (array of policy objects, up to 50). Response `201 {"agent": {...}, "agent_key": "hsk....", "note": ...}`: the key is returned only here and by `POST /agents/:id/rotate-key`.

Lifecycle: `POST /agents/:id/kill` (revokes live tokens), `POST /agents/:id/restore`, `POST /agents/:id/rotate-key`, `POST /agents/:id/policies`, `DELETE /policies/:id`.

## Agent-side calls

`POST /v1/token` body `{"scope": "...", "purpose": "<=500 chars", "ttl": <seconds, optional>}`

| Status | Body | Agent should |
|---|---|---|
| 200 | `access_token`, `token_type`, `expires_in`, `expires_at`, `scope`, `jti` | use until near `expires_at` |
| 202 | `status: pending`, `request_id`, `poll`, `expires_at`, `message` | poll `GET /v1/requests/:id` every 2 s until approved, denied or expired; never ask again while pending |
| 400 `invalid_request` | `issues` | fix, do not retry unchanged |
| 401 `missing_agent_key`, `invalid_agent_key` | | stop, alert the owner |
| 403 `scope_not_allowed` | `scope`, `message` | do not retry; ask an admin for a policy |
| 403 `agent_killed` | | stop all work |
| 429 `rate_limited` | `Retry-After` | wait, then retry |

`GET /v1/requests/:id` statuses: `pending`, `approved` (with `access_token`, `token_type`, `token_expires_at`, `jti`; or `token_state: "revoked"` and no token), `denied`, `expired` (`decided_at` set). An approved request returns the token on every poll, even after it expired: check `token_expires_at`.

`ANY /v1/proxy/<connector>/<path>?<query>` with `Authorization: Bearer <access_token>`. Only `accept`, `accept-language`, `content-type`, `if-none-match`, `x-request-id` reach the upstream. Errors: `400 invalid_path` (`..` or `.` segments, control characters, backslashes, or a path over 2048 characters), `401 missing_token|invalid_token|token_revoked` (single-use spent adds `reason: token_consumed`), `403 scope_mismatch` (body has `required` and `token_scope`), `403 agent_killed`, `404 connector_not_found`, `413` body over 2 MiB, `429`, `502 upstream_unreachable|upstream_too_large|upstream_body_failed`. Redirects are not followed; responses are buffered (10 MiB, 30 s).

`POST /v1/events` body `{"action": "<1..80 chars a-z0-9_.:->", "target": "<=300", "detail": {<=8192 chars}}` appends `agent.<action>` to the audit chain. Never put secrets in it.

`POST /v1/lease` body `{"connector": "...", "purpose": "..."}` returns `secret`, `header`, `prefix`, `base_url`, `expires_in` (advice: the broker cannot recall a leased secret).

## Minimal clients

Node (no dependencies, Node 20+):

```js
const BASE = process.env.HISAR_URL.replace(/\/$/, "");
const KEY = process.env.HISAR_AGENT_KEY;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function hisar(method, path, { body, headers = {} } = {}) {
  const res = await fetch(BASE + path, { method, headers: { ...(body === undefined ? {} : { "content-type": "application/json" }), ...headers }, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await res.text(); let data; try { data = JSON.parse(text); } catch { data = text; }
  return { status: res.status, headers: res.headers, data };
}
const asAgent = { "x-hisar-agent-key": KEY };

export async function getToken(scope, { purpose, ttl, waitMs = 5 * 60_000 } = {}) {
  const r = await hisar("POST", "/v1/token", { body: { scope, purpose, ttl }, headers: asAgent });
  if (r.status === 200) return r.data.access_token;
  if (r.status !== 202) throw new Error(`token request failed: ${r.status} ${r.data.error ?? ""}`);
  const giveUpAt = Math.min(Date.now() + waitMs, Date.parse(r.data.expires_at));
  while (Date.now() < giveUpAt) {
    await sleep(2000);
    const p = await hisar("GET", r.data.poll, { headers: asAgent });
    if (p.data.status === "approved") { if (p.data.access_token) return p.data.access_token; throw new Error("approved but token revoked"); }
    if (p.data.status === "denied") throw new Error("a human denied this request");
    if (p.data.status === "expired") throw new Error("nobody decided before the request expired");
  }
  throw new Error("gave up waiting for approval");
}
export const call = (token, connector, method, path, body) => hisar(method, `/v1/proxy/${connector}${path}`, { body, headers: { authorization: `Bearer ${token}` } });
```

Python (standard library) is in `examples/agent.py` of the broker repository: `HisarAgent(url, key).token(scope, purpose=..., ttl=...)` blocks while a human approves; `.call(token, connector, "GET", "/contacts?limit=20")` returns `(status, body)`.

## Verifying a token in your own service

Fetch `GET <broker>/.well-known/jwks.json`, verify ES256 with the broker's issuer and audience `hisar-broker`, then check that `payload.scope` covers what the service needs (same `*` rule). Offline verification cannot see revocation; keep TTLs short or call `POST /admin/api/introspect` from a trusted backend.

## Evidence and audit

`GET /admin/api/audit`, `/audit/verify`, `/audit/checkpoint` (signed), `/audit/export` (NDJSON), `GET /admin/api/evidence?from=&to=[&format=html]` (signed bundle with least-privilege findings `wildcard_policy`, `gated_scope_overlapped`, `agent_without_owner`, `policy_unused`). The linter in this skill reproduces the first three findings before the policies are applied.
