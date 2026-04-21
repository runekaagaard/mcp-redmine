# Design: Self-host mcp-redmine on EC2 for Bedrock AgentCore

**Date:** 2026-04-21
**Author:** anhvt@caerux.com
**Status:** Draft — pending review

## Problem

`mcp-redmine` is a stdio-only MCP server. Amazon Bedrock AgentCore Runtime cannot consume stdio MCP servers; it requires **streamable-http** transport on `/mcp`. We need to deploy the fork (`crx-anhvt/mcp-redmine`) on EC2 so a Bedrock Agent (via AgentCore Gateway) can invoke Redmine tools.

## Goals

- Single Bedrock agent consumes Redmine tools via an MCP endpoint.
- Reuse existing infra: Cloudflare (edge TLS + WAF), nginx on EC2, `redmine.caeruxlab.com` as the upstream Redmine instance.
- Minimal ops surface: one service, one container, one config directory.
- Rotatable secrets; zero-downtime image updates.

## Non-goals

- Multi-tenant or multi-agent access. Auth is a single shared secret.
- Hosting in AgentCore Runtime (AWS-managed microVMs) — this design is explicitly for self-managed EC2 behind AgentCore Gateway.
- Supporting stdio clients (Claude Code, local usage) from the same deployment. The fork's existing stdio entrypoint remains unchanged; this design adds a parallel HTTP entrypoint.

## Architecture

```
Bedrock Agent (AgentCore Runtime)
         │
         ▼
AgentCore Gateway (MCP target)
  • Injects header: X-MCP-Token: <secret>
  • Calls https://mcp-redmine.caeruxlab.com/mcp
         │
         ▼  (public internet, TLS by Cloudflare)
Cloudflare
  • TLS termination at edge
  • WAF Skip rule on X-MCP-Token header
         │
         ▼
EC2 instance (existing nginx host)
  ├── nginx (:80, plaintext — Cloudflare Flexible SSL)
  │     • server_name mcp-redmine.caeruxlab.com
  │     • Validates X-MCP-Token via map directive (absent/wrong → 401)
  │     • proxy_pass http://127.0.0.1:8000
  │
  └── systemd → Docker Compose
        └── mcp-redmine container
              • Image: built locally on EC2 from ./src (no registry)
              • FastMCP streamable-http on 0.0.0.0:8000/mcp (stateless_http=True)
              • Reads REDMINE_URL + REDMINE_API_KEY from .env
              • Outbound → https://redmine.caeruxlab.com
```

### Request flow

1. Bedrock agent invokes a tool; AgentCore Gateway composes a JSON-RPC request and POSTs to `https://mcp-redmine.caeruxlab.com/mcp` with the injected `X-MCP-Token` header.
2. Cloudflare matches the WAF Skip rule, forwards to the EC2 origin.
3. nginx verifies the header; on success, proxies to `127.0.0.1:8000/mcp`.
4. FastMCP dispatches to the appropriate tool (e.g., `redmine_request`), which calls Redmine's REST API with the configured Basic-Auth + API key.
5. Response flows back through the chain.

### Statelessness

`stateless_http=True`. The mcp-redmine tools are idempotent request/response calls to Redmine; no server-side session state is needed. This avoids sticky-session complexity in nginx and allows horizontal scaling later if required.

## Components

### 1. Fork changes — `crx-anhvt/mcp-redmine`

The fork's `mcp_redmine/server.py` already has argparse-based transport selection supporting `stdio` and `sse`. Extend it to also support `streamable-http` (Bedrock AgentCore requires this; it is a different protocol from SSE).

- **`mcp_redmine/server.py`** — `main()` already has `--host` and `--port` arguments for the existing `sse` transport; only the `--transport` choices list and the conditional need extending:
  ```python
  # Existing: choices=["stdio", "sse"]
  parser.add_argument(
      "--transport",
      choices=["stdio", "sse", "streamable-http"],
      default="stdio",
      help="Transport type (default: stdio)",
  )
  # ... --host and --port already exist and are reused as-is.

  # Existing: if args.transport == "sse": ...
  if args.transport in ("sse", "streamable-http"):
      mcp.settings.host = args.host
      mcp.settings.port = args.port
      if args.transport == "streamable-http":
          mcp.settings.stateless_http = True
  mcp.run(transport=args.transport)
  ```
- **`Dockerfile`** — existing file (python:3.13-slim + `uv sync`) stays structurally the same. Drop the stray trailing `"main"` token from the CMD (argparse would reject it as an unknown positional) and add transport flags:
  ```dockerfile
  FROM python:3.13-slim
  WORKDIR /app
  COPY . /app
  RUN pip install --upgrade pip && pip install uv && uv sync
  EXPOSE 8000
  CMD ["uv", "run", "--directory", "/app", "-m", "mcp_redmine.server", \
       "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
  ```
  Why no `main`: `python -m mcp_redmine.server` triggers the module's `if __name__ == "__main__": main()` block. Any extra positional like `main` is forwarded to `sys.argv` and argparse rejects it. Stdio usage for local Claude Code continues to work via the existing entry points (e.g., `uvx mcp-redmine`) — it does not use this Docker image.
- **No registry / CI needed.** The image is built directly on the EC2 from a cloned copy of the fork; see §2 EC2 layout.

### 2. EC2 layout

```
/opt/mcp-redmine/
├── src/                     # git clone of crx-anhvt/mcp-redmine
├── docker-compose.yml       # builds from ./src
├── .env                     # mode 600, owner root
└── README.md                # short ops notes
```

The EC2 builds the image locally from the cloned fork — no external registry involved.

**`docker-compose.yml`:**
```yaml
services:
  mcp-redmine:
    build: ./src
    container_name: mcp-redmine
    restart: unless-stopped
    env_file: .env
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/mcp', timeout=3).status < 500 else 1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s
    logging:
      driver: journald
      options:
        tag: mcp-redmine
```

The healthcheck treats any sub-500 response as healthy (the FastMCP streamable-http endpoint returns 4xx for GET without a proper JSON-RPC body, which still proves the process is up).

**`.env`** (mode 600, never committed to git — see `.claude/rules/2-dotenv-environments.md`):
```
REDMINE_URL=https://<BASIC_AUTH_USER>:<BASIC_AUTH_PASSWORD>@redmine.caeruxlab.com
REDMINE_API_KEY=<REDMINE_API_KEY>
```

The operator populates these values on the EC2 directly from the existing Redmine nginx Basic-Auth credentials and a Redmine account's API key (account settings → API access key). If the values previously shared during brainstorming were exposed in an earlier draft of this spec, rotate the Redmine password and regenerate the API key before deploy.

### 3. systemd unit — `/etc/systemd/system/mcp-redmine.service`

```ini
[Unit]
Description=MCP Redmine (FastMCP streamable-http)
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/mcp-redmine
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/bin/sh -c 'git -C src pull && /usr/bin/docker compose up -d --build'
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

Operational commands:
- `systemctl start mcp-redmine` / `stop` / `status`
- `systemctl reload mcp-redmine` — `git pull` the fork, rebuild image, recreate container
- `systemctl enable mcp-redmine` — start on boot
- `journalctl -u mcp-redmine -f` — systemd + (via journald driver) container logs

### 4. nginx site — `/etc/nginx/sites-available/mcp-redmine.conf`

Cloudflare handles TLS at the edge. Origin serves plain HTTP on port 80 (Cloudflare SSL mode: **Flexible**). No cert on the EC2.

```nginx
# /etc/nginx/conf.d/mcp-redmine-auth.conf (or inside http{} block)
map $http_x_mcp_token $mcp_auth_ok {
    default                0;
    "<SECRET_TOKEN>"       1;
    # During rotation, add the new token here alongside the old for ~5 minutes:
    # "<NEW_SECRET_TOKEN>" 1;
}

server {
    listen 80;
    server_name mcp-redmine.caeruxlab.com;

    # Reject requests that didn't match the map
    if ($mcp_auth_ok != 1) {
        return 401;
    }

    # Allow larger payloads for redmine_upload
    client_max_body_size 25M;

    location /mcp {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;

        # Required for streamable-http / SSE-style responses
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    access_log /var/log/nginx/mcp-redmine.access.log;
    error_log  /var/log/nginx/mcp-redmine.error.log;
}
```

Using `map` instead of a raw `if ($http_header = ...)` sidesteps nginx's well-known "if is evil" quirks in `server{}` context and makes token rotation a one-line edit. Note Cloudflare's free-plan proxy timeout caps at ~100s, so the 300s `proxy_read_timeout` is a generous ceiling but not the effective max.

Save nginx config to infra/nginx/mcp-redmine.conf.

Security note: With Cloudflare Flexible SSL, traffic between Cloudflare and the EC2 origin is **unencrypted**. This is acceptable only because the `X-MCP-Token` is the sole auth factor and Cloudflare's WAF already filters the origin. Tighten to Full (Strict) with an Origin Cert later if the threat model changes.

### 5. Cloudflare

- **DNS**: `mcp-redmine` A record → EC2 public IP, proxied (orange cloud).
- **WAF → Custom rule** "Allow MCP Redmine" (same product as the existing "Allow Redmine API" rule — not the "Security Rules" beta UI):
  - Expression: `(len(http.request.headers["x-mcp-token"]) > 0) and (http.host eq "mcp-redmine.caeruxlab.com")`
  - Action: **Skip** — same skip list used for the Redmine API rule (all remaining custom rules, all managed rules, Super Bot Fight Mode, Browser Integrity Check, Security Level).
- **SSL/TLS**: **Flexible** (Cloudflare terminates TLS; origin stays on HTTP :80). Can upgrade to Full (Strict) later with an Origin Cert.

### 6. Bedrock AgentCore Gateway target

- Target type: **MCP**.
- Endpoint: `https://mcp-redmine.caeruxlab.com/mcp`.
- Header injection: `X-MCP-Token: <secret>` — stored in AWS Secrets Manager, referenced by the target config.

## Secrets

| Secret | Stored in | Used by |
|---|---|---|
| `X-MCP-Token` | AWS Secrets Manager (Gateway side); nginx config (validation side) | Gateway → nginx |
| `REDMINE_URL` with basic-auth creds | `/opt/mcp-redmine/.env` (mode 600) | Container |
| `REDMINE_API_KEY` | `/opt/mcp-redmine/.env` (mode 600) | Container |

**Generation:** `openssl rand -hex 32` for the MCP token.

**Rotation (zero-downtime):**
1. Generate new token.
2. Add the new token as a second accepted value in the nginx `map` block (alongside the old one); `systemctl reload nginx`.
3. Update Secrets Manager with the new token; AgentCore Gateway picks it up.
4. Remove old token from the nginx `map` block; `systemctl reload nginx`.

## Error handling

| Failure | Surface | Recovery |
|---|---|---|
| Missing/invalid `X-MCP-Token` | nginx returns 401 | Check Secrets Manager value vs nginx config |
| Container crash | nginx returns 502 | `restart: unless-stopped` auto-restarts; compose healthcheck flags unhealthy state |
| Upstream Redmine 5xx | Container returns JSON-RPC error to Gateway | Bedrock surfaces tool error to the agent |
| Cloudflare WAF block | 403 at edge | Review Cloudflare firewall events dashboard |
| EC2 disk full (logs) | Service may crash-loop | journald rotation; optional CloudWatch shipping |

## Observability

**v1 — minimal:**
- `journalctl -u mcp-redmine` for container + systemd events (via journald log driver).
- `/var/log/nginx/mcp-redmine.access.log` for inbound traffic.
- Cloudflare firewall events dashboard for edge visibility.

**Deferred:**
- CloudWatch Agent shipping journald + nginx logs to a log group.
- Metrics (request count, p95 latency) via a Prometheus scrape endpoint on the MCP service.

## Deploy

**Initial setup:**
1. Create `mcp-redmine` DNS record on Cloudflare (proxied). Set SSL/TLS mode to **Flexible**.
2. `mkdir -p /opt/mcp-redmine && chown root:root /opt/mcp-redmine && chmod 750 /opt/mcp-redmine`.
3. `git clone https://github.com/crx-anhvt/mcp-redmine /opt/mcp-redmine/src`.
4. Write `docker-compose.yml` and `.env` (mode 600).
5. Install systemd unit; `systemctl daemon-reload && systemctl enable --now mcp-redmine` (first start builds the image).
6. Place nginx site config at `/etc/nginx/sites-available/mcp-redmine.conf`, symlink to `/etc/nginx/sites-enabled/mcp-redmine.conf` (or put the `map` block in `/etc/nginx/conf.d/`), then `nginx -t && systemctl reload nginx`.
7. Add Cloudflare WAF Custom rule.
8. Register target in AgentCore Gateway with the shared token.

**Code update:**
1. Merge changes into the fork's main branch on GitHub.
2. On EC2: `systemctl reload mcp-redmine` (`git pull` + rebuild + recreate).
3. Smoke test — see **Testing** section below.

**Rollback:**
- `cd /opt/mcp-redmine/src && git log` to find the previous good SHA.
- `git checkout <sha> && cd .. && docker compose up -d --build`.

## Testing

- **Unit**: none added. The fork's tools are thin httpx wrappers over Redmine's REST API and rely on the upstream Redmine OpenAPI schema.
- **Integration (post-deploy) smoke tests:**
  1. **Auth rejection** — no token:
     ```
     curl -s -o /dev/null -w "%{http_code}\n" https://mcp-redmine.caeruxlab.com/mcp
     ```
     Expect `401`.
  2. **Auth pass / process reachable** — a GET with the valid token will not return a valid JSON-RPC body (FastMCP streamable-http requires a POST with `Accept: application/json, text/event-stream` and a JSON-RPC payload), but any **non-401** response (typically 400/405/406) proves auth passed and the upstream process is up:
     ```
     curl -s -o /dev/null -w "%{http_code}\n" \
       -H "X-MCP-Token: $TOKEN" \
       https://mcp-redmine.caeruxlab.com/mcp
     ```
     Expect any 4xx **other than 401** (or 200 if the response shape is ever simplified upstream).
  3. **MCP initialize round-trip** — full JSON-RPC smoke:
     ```
     curl -sS -X POST https://mcp-redmine.caeruxlab.com/mcp \
       -H "X-MCP-Token: $TOKEN" \
       -H "Content-Type: application/json" \
       -H "Accept: application/json, text/event-stream" \
       -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
     ```
     Expect a JSON-RPC response with `"result"` containing `serverInfo` and `capabilities`.
- **End-to-end**: in the Bedrock Gateway test console, invoke `redmine_paths_list` and verify the Redmine path catalog is returned; then invoke a concrete tool (e.g., list projects) and verify the response.

## Resolved questions

- **Cloudflare TLS**: Flexible mode. Edge TLS only; origin on HTTP :80.
- **Log retention**: journald default; no CloudWatch shipping for v1.
- **Image registry**: None. EC2 builds the image locally from a cloned copy of the fork. Single-EC2 scope makes a registry (and its credentials + CI) unnecessary.

## Decision log

| Decision | Choice | Rationale |
|---|---|---|
| Deployment model | Self-hosted on EC2 behind AgentCore Gateway | User owns existing EC2/nginx/Cloudflare stack |
| Consumers | Single Bedrock agent | Keeps auth and multi-tenancy simple |
| Network exposure | Public HTTPS via Cloudflare | Mirrors existing Redmine topology |
| Transport conversion | Patch the fork with a streamable-http entrypoint | FastMCP supports it natively; user owns the fork |
| Auth | Custom `X-MCP-Token` header | Works cleanly with Cloudflare allowlist (same pattern as Redmine API rule) |
| TLS | Cloudflare Flexible (edge only, HTTP to origin) | Matches user's existing topology; origin protected by WAF + shared token |
| Image registry | None; build on EC2 from git clone | Single-host scope; avoids registry + CI overhead |
| Runtime | Docker Compose, supervised by systemd | User preference for systemd lifecycle, retains image-based deploys |
| Secrets | `.env` file on disk, mode 600 | Simple; EC2 is a trusted host |
| HTTP statefulness | `stateless_http=True` | Tools are idempotent; no session affinity required |
