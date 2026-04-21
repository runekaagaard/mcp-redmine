# mcp-redmine EC2 Deployment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy `crx-anhvt/mcp-redmine` on an existing EC2 instance as a streamable-http MCP endpoint that a single AWS Bedrock AgentCore Gateway target can consume.

**Architecture:** EC2 builds the fork's Docker image locally from `./src`, systemd supervises Docker Compose, nginx (plain HTTP :80) reverse-proxies to the container with an `X-MCP-Token` header gate. Cloudflare Flexible SSL handles edge TLS and a WAF Custom Rule allows the MCP traffic past managed protections. Bedrock AgentCore Gateway injects the shared token from AWS Secrets Manager.

**Tech Stack:** Python 3.13 + FastMCP (streamable-http transport), `uv`, Docker Compose, systemd, nginx, Cloudflare (DNS/WAF), AWS Bedrock AgentCore Gateway + Secrets Manager.

**Spec:** [`docs/superpowers/specs/2026-04-21-mcp-redmine-ec2-design.md`](../specs/2026-04-21-mcp-redmine-ec2-design.md)

**File structure produced by this plan:**

Fork repo (`crx-anhvt/mcp-redmine`):
- Modify: `mcp_redmine/server.py` — add `streamable-http` to `--transport` choices.
- Modify: `Dockerfile` — drop stray `main` positional, add transport flags + `EXPOSE`.
- Create: `infra/nginx/mcp-redmine.conf` — reference nginx site config (checked in for source-of-truth).
- Create: `infra/systemd/mcp-redmine.service` — reference systemd unit.
- Create: `infra/README.md` — one-page operator quickstart referencing this plan.

EC2 host (`/opt/mcp-redmine/`):
- `src/` — `git clone` of the fork.
- `docker-compose.yml` — builds from `./src`.
- `.env` — mode 600, real credentials.

System files:
- `/etc/nginx/sites-available/mcp-redmine.conf` + symlink to `sites-enabled/`.
- `/etc/systemd/system/mcp-redmine.service`.

External config:
- Cloudflare: DNS A record, SSL/TLS Flexible, WAF Custom Rule.
- AWS: Secrets Manager entry, AgentCore Gateway MCP target.

---

## Chunk 1: Fork code changes

All work in this chunk happens inside the `crx-anhvt/mcp-redmine` repo on a feature branch; nothing touches the EC2 yet.

### Task 1: Branch + verify baseline

**Files:** none modified yet.

- [ ] **Step 1.1: Ensure clean working tree and create feature branch**

```bash
cd /Users/anhvt/caeruxlab/mcp-redmine
git status            # expect: no changes other than docs/ and .agent/ scaffolding
git checkout -b feat/streamable-http-bedrock
```

- [ ] **Step 1.2: Confirm existing argparse args in `mcp_redmine/server.py`**

Run: `grep -n "add_argument\|transport\|--host\|--port" mcp_redmine/server.py`
Expected output includes (around lines 253–260):
- `parser.add_argument("--transport", choices=["stdio", "sse"], ...)`
- `parser.add_argument("--host", ...)`
- `parser.add_argument("--port", ...)`

Confirms `--host` / `--port` are already defined; we only need to extend `--transport` choices and the conditional.

### Task 2: Add `streamable-http` as a transport choice

**Files:**
- Modify: `mcp_redmine/server.py` lines ~252–266 (the `main()` function).

- [ ] **Step 2.1: Edit `main()` to accept `streamable-http` and set `stateless_http`**

Current block:
```python
def main():
    """Main entry point for the mcp-redmine package."""
    import argparse
    parser = argparse.ArgumentParser(description="MCP Redmine Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio",
                        help="Transport type (default: stdio)")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE transport (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE transport (default: 8000)")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    mcp.run(transport=args.transport)
```

Replace with:
```python
def main():
    """Main entry point for the mcp-redmine package."""
    import argparse
    parser = argparse.ArgumentParser(description="MCP Redmine Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio",
                        help="Transport type (default: stdio)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Host for sse/streamable-http transport (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port for sse/streamable-http transport (default: 8000)")
    args = parser.parse_args()

    if args.transport in ("sse", "streamable-http"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        if args.transport == "streamable-http":
            mcp.settings.stateless_http = True
    mcp.run(transport=args.transport)
```

- [ ] **Step 2.2: Syntax/import sanity check**

Run: `uv run python -c "from mcp_redmine.server import main; print('ok')"`
Expected: `ok`

(Does not start the server — just imports the module to catch syntax errors.)

- [ ] **Step 2.3: Verify CLI `--help` lists the new choice**

```bash
REDMINE_URL=http://example.invalid REDMINE_API_KEY=x \
  uv run python -m mcp_redmine.server --help
```

Expected: `--transport {stdio,sse,streamable-http}` in help output. Process exits 0 after printing help.

- [ ] **Step 2.4: Commit**

```bash
git add mcp_redmine/server.py
git commit -m "feat(server): add streamable-http transport choice

Bedrock AgentCore Runtime requires streamable-http (not SSE).
Extend --transport choices and set stateless_http=True when
that transport is selected. --host/--port already existed for SSE
and are reused as-is."
```

### Task 3: Fix the Dockerfile CMD

**Files:**
- Modify: `Dockerfile` (whole file).

- [ ] **Step 3.1: Replace the entire Dockerfile content**

Current content (verified earlier):
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip \
    && pip install uv \
    && uv sync

CMD ["uv", "run", "--directory", "/app", "-m", "mcp_redmine.server", "main"]
```

New content:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip \
    && pip install uv \
    && uv sync

EXPOSE 8000

# `python -m mcp_redmine.server` auto-runs main() via the __main__ block;
# passing a positional "main" would be fed to argparse and rejected.
CMD ["uv", "run", "--directory", "/app", "-m", "mcp_redmine.server", \
     "--transport", "streamable-http", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
```

- [ ] **Step 3.2: Build the image locally to validate**

```bash
docker build -t mcp-redmine:local-test .
```

Expected: build completes without errors. Note any warnings about `uv sync` — those are acceptable as long as the final image builds.

- [ ] **Step 3.3: Smoke-start the container and verify it binds port 8000**

```bash
docker run --rm -d --name mcp-redmine-smoke \
  -e REDMINE_URL=http://example.invalid \
  -e REDMINE_API_KEY=smoketestkey \
  -p 127.0.0.1:8000:8000 \
  mcp-redmine:local-test
sleep 3
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/mcp
```

Expected HTTP code: any 4xx that is **not 000 or 500+** (typically 400/405/406 — FastMCP rejects GET without a JSON-RPC body). Code `000` means the process didn't bind; `5xx` means a server error inside FastMCP. Both are failures.

- [ ] **Step 3.4: Stop the smoke container**

```bash
docker logs mcp-redmine-smoke | tail -20   # inspect startup log; look for "Uvicorn running on http://0.0.0.0:8000"
docker rm -f mcp-redmine-smoke
```

- [ ] **Step 3.5: Commit**

```bash
git add Dockerfile
git commit -m "fix(docker): run streamable-http by default; drop stray 'main' arg

Passing 'main' as a positional to python -m mcp_redmine.server
is rejected by argparse. Module's __main__ block already invokes
main(). Image now defaults to streamable-http on 0.0.0.0:8000
for EC2/Bedrock use; stdio remains available via uvx for local
Claude Code clients."
```

### Task 4: Check in reference nginx + systemd artifacts

**Files:**
- Create: `infra/nginx/mcp-redmine.conf`
- Create: `infra/systemd/mcp-redmine.service`
- Create: `infra/README.md`

Why: the spec mentions `Save nginx config to infra/nginx/mcp-redmine.conf`. Making these files the canonical source in the repo means an operator can `cp` them onto the EC2 rather than retyping from the spec.

- [ ] **Step 4.1: Create `infra/nginx/mcp-redmine.conf`**

```nginx
# /etc/nginx/sites-available/mcp-redmine.conf (symlinked into sites-enabled/)
# The `map` must live at http{} scope; sites-available/*.conf files already
# sit inside http{} via the default include, so this is fine.

map $http_x_mcp_token $mcp_auth_ok {
    default                            0;
    "REPLACE_WITH_REAL_TOKEN"          1;
    # During rotation, temporarily accept a second value:
    # "REPLACE_WITH_NEW_TOKEN"         1;
}

server {
    listen 80;
    server_name mcp-redmine.caeruxlab.com;

    if ($mcp_auth_ok != 1) {
        return 401;
    }

    client_max_body_size 25M;

    location /mcp {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;

        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    access_log /var/log/nginx/mcp-redmine.access.log;
    error_log  /var/log/nginx/mcp-redmine.error.log;
}
```

- [ ] **Step 4.2: Create `infra/systemd/mcp-redmine.service`**

```ini
[Unit]
Description=MCP Redmine (FastMCP streamable-http, Docker Compose)
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

- [ ] **Step 4.3: Create `infra/README.md`**

```markdown
# infra/

Operator reference artifacts for the EC2 deployment described in
`docs/superpowers/specs/2026-04-21-mcp-redmine-ec2-design.md`.

- `nginx/mcp-redmine.conf` — nginx site config. Replace `REPLACE_WITH_REAL_TOKEN`
  before `cp`-ing into `/etc/nginx/sites-available/` on the EC2.
- `systemd/mcp-redmine.service` — systemd unit. Place at
  `/etc/systemd/system/mcp-redmine.service`.

See `docs/superpowers/plans/2026-04-21-mcp-redmine-ec2.md` for the step-by-step
deployment procedure.
```

- [ ] **Step 4.4: Commit**

```bash
git add infra/
git commit -m "chore(infra): check in reference nginx + systemd configs"
```

### Task 5: Push the branch and open a PR

- [ ] **Step 5.1: Push the branch**

```bash
git push -u origin feat/streamable-http-bedrock
```

- [ ] **Step 5.2: Open a PR via `gh` CLI**

```bash
gh pr create --title "feat: add streamable-http transport for Bedrock AgentCore" \
  --body "$(cat <<'EOF'
## Summary
- Add `streamable-http` to `--transport` choices in `mcp_redmine/server.py`
- Fix Dockerfile CMD (drop stray `main` positional; add transport flags)
- Check in reference nginx + systemd configs under `infra/`

## Test plan
- [ ] `docker build -t mcp-redmine:local-test .` succeeds
- [ ] Container binds `0.0.0.0:8000` and returns a non-5xx response on `GET /mcp`
- [ ] `python -m mcp_redmine.server --help` shows `streamable-http` as a choice
EOF
)"
```

- [ ] **Step 5.3: Merge after review**

Once CI/reviewer approval lands, squash-merge into `main`. EC2 deploy in Chunk 2 pulls from `main`.

---

## Chunk 2: EC2 host provisioning

All work in this chunk runs as a sudo-capable user on the target EC2 instance. Commands assume Ubuntu/Debian; adapt paths if different.

### Task 6: Generate the shared MCP token

**Files:** none modified.

- [ ] **Step 6.1: Generate a 64-char hex token on a trusted workstation**

```bash
openssl rand -hex 32
```

Record the output; you will paste it into three places: nginx config on EC2, AWS Secrets Manager, and your local ops notes (short-term). Call this value `$MCP_TOKEN` for the rest of the plan.

### Task 7: Create the EC2 working directory and clone the fork

**Files on EC2:**
- Create: `/opt/mcp-redmine/`
- Create: `/opt/mcp-redmine/src/` (git clone)

- [ ] **Step 7.1: Create the directory**

```bash
sudo mkdir -p /opt/mcp-redmine
sudo chown root:root /opt/mcp-redmine
sudo chmod 750 /opt/mcp-redmine
```

- [ ] **Step 7.2: Install Docker Compose plugin if not present**

```bash
docker compose version
```

If the command is not found, install via distro package manager (`sudo apt install docker-compose-plugin` on modern Ubuntu). Do NOT install standalone `docker-compose` v1 — the systemd unit uses the `docker compose` (v2 plugin) invocation.

- [ ] **Step 7.3: Clone the fork**

```bash
sudo git clone https://github.com/crx-anhvt/mcp-redmine /opt/mcp-redmine/src
sudo git -C /opt/mcp-redmine/src checkout main  # pin to main; change if you want a tag
```

- [ ] **Step 7.4: Verify the checked-out Dockerfile contains the transport flags**

```bash
grep -A4 '^CMD' /opt/mcp-redmine/src/Dockerfile
```

Expected to include `"--transport", "streamable-http"`.

### Task 8: Write `docker-compose.yml` and `.env`

**Files on EC2:**
- Create: `/opt/mcp-redmine/docker-compose.yml`
- Create: `/opt/mcp-redmine/.env` (mode 600)

- [ ] **Step 8.1: Write `docker-compose.yml`**

```bash
sudo tee /opt/mcp-redmine/docker-compose.yml >/dev/null <<'YAML'
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
YAML
```

- [ ] **Step 8.2: Write `.env` (placeholders — replace with real values)**

```bash
sudo tee /opt/mcp-redmine/.env >/dev/null <<'ENV'
REDMINE_URL=https://<BASIC_AUTH_USER>:<BASIC_AUTH_PASSWORD>@redmine.caeruxlab.com
REDMINE_API_KEY=<REDMINE_API_KEY>
ENV
sudo chmod 600 /opt/mcp-redmine/.env
sudo chown root:root /opt/mcp-redmine/.env
```

Then edit the file in place (`sudo vim /opt/mcp-redmine/.env`) and replace the three placeholders with real values. Verify:

```bash
sudo stat -c '%a %U:%G %n' /opt/mcp-redmine/.env
```

Expected: `600 root:root /opt/mcp-redmine/.env`.

- [ ] **Step 8.3: First build + start (dry run, not yet via systemd)**

```bash
cd /opt/mcp-redmine
sudo docker compose up -d --build
sudo docker compose ps
```

Expected: one service, STATE `running (healthy)` after ~30s (run `docker compose ps` again if the first check was during `start_period`).

- [ ] **Step 8.4: Local reachability check**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/mcp
```

Expected: non-500 4xx (typically 400/405/406). Code 000 = process not listening; fix before proceeding.

- [ ] **Step 8.5: Stop the ad-hoc container (systemd will take over)**

```bash
sudo docker compose down
```

### Task 9: Install the systemd unit

**Files:**
- Create: `/etc/systemd/system/mcp-redmine.service`

- [ ] **Step 9.1: Copy the checked-in unit file from the clone**

```bash
sudo cp /opt/mcp-redmine/src/infra/systemd/mcp-redmine.service /etc/systemd/system/mcp-redmine.service
sudo chmod 644 /etc/systemd/system/mcp-redmine.service
```

- [ ] **Step 9.2: Enable and start**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mcp-redmine
```

- [ ] **Step 9.3: Verify service is active**

```bash
sudo systemctl status mcp-redmine --no-pager
sudo docker compose -f /opt/mcp-redmine/docker-compose.yml ps
```

Expected: `Active: active (exited)` (because `Type=oneshot RemainAfterExit=yes`), and `docker compose ps` shows the container running.

- [ ] **Step 9.4: Tail logs for sanity**

```bash
sudo journalctl -u mcp-redmine -n 50 --no-pager
```

Expected: no error backtraces; lifecycle entries present.

### Task 10: Configure nginx

**Files:**
- Create: `/etc/nginx/sites-available/mcp-redmine.conf`
- Symlink: `/etc/nginx/sites-enabled/mcp-redmine.conf`

- [ ] **Step 10.1: Copy and substitute the token**

```bash
sudo cp /opt/mcp-redmine/src/infra/nginx/mcp-redmine.conf \
       /etc/nginx/sites-available/mcp-redmine.conf
sudo sed -i "s/REPLACE_WITH_REAL_TOKEN/$MCP_TOKEN/" /etc/nginx/sites-available/mcp-redmine.conf
```

(Use the value from Task 6. Double-quote-escape if the token were to contain special chars; with `openssl rand -hex 32` it's all hex, so safe.)

- [ ] **Step 10.2: Symlink into sites-enabled**

```bash
sudo ln -s /etc/nginx/sites-available/mcp-redmine.conf /etc/nginx/sites-enabled/mcp-redmine.conf
```

- [ ] **Step 10.3: Test + reload nginx**

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Expected: `syntax is ok` + `test is successful`, no reload errors.

- [ ] **Step 10.4: Local end-to-end through nginx**

```bash
# Without token
curl -sS -o /dev/null -w "%{http_code}\n" -H "Host: mcp-redmine.caeruxlab.com" \
  http://127.0.0.1/mcp
```

Expected: `401`.

```bash
# With token
curl -sS -o /dev/null -w "%{http_code}\n" -H "Host: mcp-redmine.caeruxlab.com" \
  -H "X-MCP-Token: $MCP_TOKEN" http://127.0.0.1/mcp
```

Expected: non-500 4xx (not 401), confirming auth passes and upstream is reachable.

---

## Chunk 3: Cloudflare configuration

All work in this chunk is in the Cloudflare dashboard (or via API if preferred). No EC2 changes.

### Task 11: DNS

- [ ] **Step 11.1: Add A record**

Cloudflare → DNS → Records → Add record:
- Type: `A`
- Name: `mcp-redmine`
- IPv4 address: `<EC2 public IP>`
- Proxy status: **Proxied** (orange cloud)
- TTL: Auto

- [ ] **Step 11.2: Verify DNS resolves via Cloudflare**

From a workstation:
```bash
dig +short mcp-redmine.caeruxlab.com
```

Expected: a Cloudflare anycast IP (104.x / 172.x range), not the EC2 IP directly.

### Task 12: SSL/TLS mode

- [ ] **Step 12.1: Set SSL/TLS mode to Flexible**

Cloudflare → SSL/TLS → Overview → Custom SSL/TLS → set mode to **Flexible**.

Rationale: origin serves HTTP on :80; Cloudflare terminates TLS at the edge. The shared token + WAF rule are the auth surface.

- [ ] **Step 12.2: Verify HTTPS works end-to-end (without token, expect 401)**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://mcp-redmine.caeruxlab.com/mcp
```

Expected: `401` (Cloudflare gets a valid edge cert automatically; traffic reaches nginx which rejects due to missing token).

If you get `520`/`525`/`526`, double-check SSL/TLS mode is Flexible (not Full / Full Strict).

### Task 13: WAF Custom Rule

- [ ] **Step 13.1: Create the rule**

Cloudflare → Security → **WAF** → **Custom rules** → Create rule:
- Rule name: `Allow MCP Redmine`
- When incoming requests match: use the Expression Editor and paste:
  ```
  (len(http.request.headers["x-mcp-token"]) > 0) and (http.host eq "mcp-redmine.caeruxlab.com")
  ```
- Action: **Skip**
- Skip the following:
  - [x] All remaining custom rules
  - [x] All managed rules
  - [x] All Super Bot Fight Mode rules
  - [x] Browser Integrity Check
  - [x] Security Level
- Deploy.

- [ ] **Step 13.2: Verify the rule is matching**

From a workstation, send a request with the header:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "X-MCP-Token: $MCP_TOKEN" \
  https://mcp-redmine.caeruxlab.com/mcp
```

Expected: non-500 4xx (not 401, not 403).

Then check Cloudflare → Security → Events and confirm a recent event with `Action: skip` and `Rule: Allow MCP Redmine` for this request.

---

## Chunk 4: AgentCore Gateway + smoke tests

All work in this chunk is in AWS (Secrets Manager + AgentCore Gateway) plus final verification. No EC2 changes.

### Task 14: Store the token in Secrets Manager

- [ ] **Step 14.1: Create secret**

AWS Console → Secrets Manager → Store a new secret:
- Secret type: Other type of secret
- Key/value: `token` → `<MCP_TOKEN>`
- Secret name: `mcp-redmine/x-mcp-token`
- Encryption key: default (`aws/secretsmanager`)
- No rotation for v1.

(Or via CLI:)
```bash
aws secretsmanager create-secret \
  --name mcp-redmine/x-mcp-token \
  --secret-string "{\"token\":\"$MCP_TOKEN\"}"
```

- [ ] **Step 14.2: Note the secret ARN**

Record the ARN — the Gateway target configuration will reference it.

### Task 15: Register the MCP target in AgentCore Gateway

- [ ] **Step 15.1: Create (or reuse) a Gateway**

AWS Console → Bedrock → AgentCore → Gateways. If no Gateway exists, create one — name it e.g. `caeruxlab-tools`. Otherwise reuse the existing Gateway the Bedrock agent is bound to.

- [ ] **Step 15.2: Add an MCP target**

Gateway → Targets → Add target:
- Target type: **MCP**
- Name: `mcp-redmine`
- Endpoint: `https://mcp-redmine.caeruxlab.com/mcp`
- Custom request headers:
  - Header name: `X-MCP-Token`
  - Value source: Secrets Manager → select `mcp-redmine/x-mcp-token` → key `token`

Deploy the target.

- [ ] **Step 15.3: Wait for target status = READY**

Gateway → Targets → `mcp-redmine` → Status should transition to READY within ~1–2 minutes.

### Task 16: End-to-end smoke tests

- [ ] **Step 16.1: From-laptop JSON-RPC initialize**

```bash
curl -sS -X POST https://mcp-redmine.caeruxlab.com/mcp \
  -H "X-MCP-Token: $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
```

Expected: a JSON-RPC response (possibly SSE-framed if `text/event-stream` is returned) containing `"result"` with `serverInfo` and `capabilities`.

- [ ] **Step 16.2: Gateway test console — `redmine_paths_list`**

AWS Console → Bedrock → AgentCore → Gateways → your gateway → Test → invoke tool `redmine_paths_list` (no args).

Expected: response lists Redmine API paths (issues, projects, users, etc.).

- [ ] **Step 16.3: Gateway test console — list Redmine projects**

Invoke `redmine_request` with:
```json
{"path": "/projects.json", "method": "get"}
```

Expected: JSON body with `projects: [...]` array (may be empty if the bound Redmine account has no visible projects; the absence of an error is the pass criterion).

- [ ] **Step 16.4: From Bedrock agent**

In the Bedrock agent you plan to attach this Gateway to, run a prompt that should trigger a Redmine tool (e.g., "list the projects available in Redmine"). Verify the agent returns the expected data.

- [ ] **Step 16.5: Commit operational notes**

If anything diverged from this plan (IPs, Gateway ARN, target name), record the final values in `infra/README.md` on a follow-up branch and merge. This is the last chance to capture tacit knowledge while it's fresh.

---

## Rollback (reference)

If Chunk 2 or later fails:

```bash
# Stop and disable service
sudo systemctl disable --now mcp-redmine

# Remove nginx site
sudo rm /etc/nginx/sites-enabled/mcp-redmine.conf
sudo nginx -t && sudo systemctl reload nginx

# Remove DNS record + WAF rule in Cloudflare
# Delete AgentCore target + Secrets Manager secret in AWS
```

To roll back to a previous fork commit after a bad deploy:
```bash
cd /opt/mcp-redmine/src
sudo git log --oneline -n 10
sudo git checkout <previous-good-sha>
cd /opt/mcp-redmine
sudo docker compose up -d --build
```
