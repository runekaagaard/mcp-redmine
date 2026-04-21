# infra/

Operator reference artifacts for the EC2 deployment described in
`docs/superpowers/specs/2026-04-21-mcp-redmine-ec2-design.md`.

- `nginx/mcp-redmine.conf` — nginx site config. Replace `REPLACE_WITH_REAL_TOKEN`
  before `cp`-ing into `/etc/nginx/sites-available/` on the EC2.
- `systemd/mcp-redmine.service` — systemd unit. Place at
  `/etc/systemd/system/mcp-redmine.service`.

See `docs/superpowers/plans/2026-04-21-mcp-redmine-ec2.md` for the step-by-step
deployment procedure.
