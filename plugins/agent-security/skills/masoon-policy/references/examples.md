# Worked examples

## 1. Read-mostly CRM digest bot

Need: read contacts weekly, create a contact occasionally after a human says yes.

```json
{
  "connectors": [
    {"name": "crm-read", "base_url": "https://api.example-crm.com", "secret": "${CRM_TOKEN}"},
    {"name": "crm-write", "base_url": "https://api.example-crm.com", "secret": "${CRM_TOKEN}"}
  ],
  "agents": [{
    "name": "mailbot", "owner": "growth-team", "description": "Weekly contact digest; may create one contact per approval.",
    "policies": [
      {"scope_pattern": "crm-read:GET:/contacts", "max_ttl": 120},
      {"scope_pattern": "crm-read:GET:/contacts/*", "max_ttl": 120},
      {"scope_pattern": "crm-write:POST:/contacts", "max_ttl": 60, "requires_approval": true, "single_use": true}
    ]
  }]
}
```

Agent asks `crm-read:GET:/contacts*` with purpose "weekly digest" and gets a 120 s token; asks `crm-write:POST:/contacts` with purpose "add Ada Lovelace from inbound form 1234", gets 202, polls, a human approves in the dashboard, the token works for exactly one call.

## 2. Coding agent with GitHub through hisar-mcp

Need: the MCP GitHub server runs under the gateway; reads are free, writes need approval.

```json
{
  "connectors": [{"name": "github", "base_url": "https://api.github.com", "secret": "${GITHUB_TOKEN}"}],
  "agents": [{
    "name": "claude-code-github", "owner": "basit", "description": "Claude Code via hisar-mcp; upstream name github.",
    "policies": [
      {"scope_pattern": "lease:github", "max_ttl": 300},
      {"scope_pattern": "mcp:github:get_*", "max_ttl": 300},
      {"scope_pattern": "mcp:github:list_*", "max_ttl": 300},
      {"scope_pattern": "mcp:github:search_*", "max_ttl": 300},
      {"scope_pattern": "mcp:github:create_issue", "max_ttl": 60, "requires_approval": true},
      {"scope_pattern": "mcp:github:create_pull_request", "max_ttl": 60, "requires_approval": true, "single_use": true},
      {"scope_pattern": "mcp:github:push_files", "max_ttl": 60, "requires_approval": true, "single_use": true}
    ]
  }]
}
```

The lease lets the gateway start the real server with the token in its environment (`HISAR_LEASE_ENV=GITHUB_PERSONAL_ACCESS_TOKEN=github`). Tools not listed (`delete_*`, `merge_*`) are refused.

## 3. What the linter rejects

| Bundle fragment | Finding | Fix |
|---|---|---|
| `"scope_pattern": "crm:get:/x"` | error `method_case` | `crm:GET:/x` |
| `"scope_pattern": "*"` | warning `wildcard_policy` | name connector and method |
| `"scope_pattern": "crm:*"` ungated next to gated `crm:POST:/contacts` | warning `gated_scope_overlapped` | split into `crm-read` and `crm-write` connectors |
| `"scope_pattern": "lease:github", "requires_approval": true` | error `lease_gated` | gate the tool scopes instead |
| `"max_ttl": 5` | error `max_ttl` | 10 to 86400 |
| `"secret": "ghp_..."` literal | error `secret_literal` | `"${GITHUB_TOKEN}"` |
| agent without `owner` | warning `agent_without_owner` | set the accountable team |
