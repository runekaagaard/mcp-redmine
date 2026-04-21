---
phase: monitoring
title: Monitoring & Observability
description: Define monitoring strategy, metrics, alerts, and incident response
template_usage: Copy this file to feature-{name}.md and fill in each section
created_at: {{datetime}}
updated_at: {{datetime}}
---

# Monitoring & Observability

> **Template**: Copy to `feature-{name}.md` before editing. Run `/review-monitoring` to validate.

**Related docs**: [Implementation](../implementation/) | [Testing](../testing/) | [Deployment](../deployment/)
**Applicable rules/skills**: AI Model Auto Decision Making

## Key Metrics
**What do we need to track?**

Define metrics before launch so dashboards and alerts can be set up alongside the deployment.

### Performance Metrics

| Metric | Source | Baseline | Alert threshold | Dashboard |
|--------|--------|----------|----------------|-----------|
| Response time (p50, p95, p99) | [APM / logs] | [current value] | [p95 > Xms] | [link] |
| Throughput (rps) | [APM / LB metrics] | [current value] | [< X rps sustained] | [link] |
| CPU utilization | [infra monitoring] | [current %] | [> X%] | [link] |
| Memory utilization | [infra monitoring] | [current %] | [> X%] | [link] |

### Business Metrics

| Metric | What it measures | Source | Expected range |
|--------|-----------------|--------|---------------|
| [e.g., Sign-up conversion] | [% of visitors who sign up] | [analytics] | [X-Y%] |
| [e.g., Feature adoption] | [% of users using new feature] | [events / flags] | [target %] |
| [e.g., Transaction success rate] | [% of successful operations] | [logs / DB] | [> X%] |

### Error Metrics

| Metric | Source | Alert threshold | Notes |
|--------|--------|----------------|-------|
| Error rate (5xx) | [APM / logs] | [> X% of requests] | Ensure error responses are generic to users (per `cxl-security-review`) |
| Failed background jobs | [queue / logs] | [> X failures per hour] | |
| Unhandled exceptions | [error tracker] | [any new exception type] | Detailed errors in server logs only, never exposed to clients |
| Client-side errors (if applicable) | [browser monitoring] | [> X% sessions affected] | |

## Monitoring Tools
**What tools are we using and how are they configured?**

| Purpose | Tool | Access | Owner |
|---------|------|--------|-------|
| Application Performance (APM) | [e.g., Datadog, New Relic, OpenTelemetry] | [URL / how to access] | [Who manages] |
| Infrastructure monitoring | [e.g., CloudWatch, Prometheus + Grafana] | [URL] | [Who] |
| Log aggregation | [e.g., ELK, Loki, CloudWatch Logs] | [URL] | [Who] |
| Error tracking | [e.g., Sentry, Bugsnag] | [URL] | [Who] |
| User analytics | [e.g., Mixpanel, Amplitude, PostHog] | [URL] | [Who] |
| Uptime monitoring | [e.g., Pingdom, UptimeRobot] | [URL] | [Who] |

## Logging Strategy
**What do we log and how?**

- What structured logging format do we use?
  ```json
  {
    "timestamp": "ISO-8601",
    "level": "info|warn|error",
    "service": "service-name",
    "trace_id": "correlation-id",
    "message": "human-readable message",
    "context": { "userId": "...", "action": "..." }
  }
  ```
- What log levels are used and when?
  - `error`: Failures requiring investigation or intervention
  - `warn`: Unexpected conditions that are handled but notable
  - `info`: Significant business events (request completed, user action)
  - `debug`: Detailed diagnostic info (disabled in production)
- What is the log retention policy (e.g., 30 days hot, 1 year cold)?
- What sensitive data must never appear in logs? Per `cxl-security-review`: never log passwords, tokens, API keys, card numbers, or PII. Use redaction (e.g., log `{ email, userId }` not `{ email, password }`).
- How are logs searched and correlated across services (trace IDs, request IDs)?

## Alerts & Notifications
**When and how do we get notified?**

### Critical Alerts (page immediately)

| Alert name | Condition | Channel | Runbook |
|-----------|-----------|---------|---------|
| [e.g., High error rate] | [5xx rate > 5% for 5 min] | [PagerDuty / Slack] | [Link to runbook] |
| [e.g., Service down] | [Health check fails 3x consecutive] | [PagerDuty] | [Link] |
| [e.g., Database connection exhaustion] | [Pool usage > 90%] | [PagerDuty] | [Link] |

### Warning Alerts (review next business day)

| Alert name | Condition | Channel | Action |
|-----------|-----------|---------|--------|
| [e.g., Elevated latency] | [p95 > 500ms for 15 min] | [Slack] | [Investigate cause] |
| [e.g., Disk usage high] | [> 80% capacity] | [Slack] | [Clean up or expand] |
| [e.g., Job queue backing up] | [Queue depth > X for 10 min] | [Slack] | [Scale workers] |

- How do we avoid alert fatigue (tuning thresholds, deduplication, snooze policies)?
- How often do we review and update alert thresholds?

## Dashboards
**What do we visualize?**

| Dashboard | Audience | Key widgets | Link |
|-----------|----------|-------------|------|
| System health | Engineering on-call | Error rates, latency, throughput, resource usage | [URL] |
| Business metrics | Product / leadership | Conversion, feature usage, user growth | [URL] |
| Deployment tracking | Engineering | Recent deploys, rollback history, deploy duration | [URL] |
| [Custom] | [Who] | [What] | [URL] |

## Incident Response
**How do we handle issues?**

### On-Call Rotation

| Role | Schedule | Contact | Escalation |
|------|----------|---------|-----------|
| Primary on-call | [e.g., weekly rotation, Mon 9am handoff] | [Slack handle / phone] | [Escalate to secondary after X min] |
| Secondary on-call | [schedule] | [contact] | [Escalate to engineering lead] |
| Engineering lead | [always available as escalation] | [contact] | |

### Incident Severity Levels

| Severity | Definition | Response time | Example |
|----------|-----------|---------------|---------|
| SEV-1 | Complete outage or data loss | < 15 minutes | Service unreachable, data corruption |
| SEV-2 | Major feature broken, workaround exists | < 1 hour | Payments failing for subset of users |
| SEV-3 | Minor degradation, no immediate user impact | Next business day | Elevated latency, non-critical job failures |

### Incident Process
1. **Detect & triage** -- Alert fires or report received; on-call acknowledges and assigns severity
2. **Communicate** -- Post in incident channel; update status page if user-facing
3. **Investigate & diagnose** -- Check dashboards, logs, recent deploys; identify root cause
4. **Resolve & mitigate** -- Apply fix or rollback; confirm metrics return to normal
5. **Post-mortem** -- Write blameless post-mortem within 48 hours; identify action items to prevent recurrence

## Health Checks
**How do we verify system health?**

| Check | Endpoint / Method | What it verifies | Frequency |
|-------|-------------------|-----------------|-----------|
| Liveness | [e.g., GET /healthz] | Process is running | [e.g., every 10s] |
| Readiness | [e.g., GET /readyz] | Can serve traffic (DB connected, cache warm) | [e.g., every 10s] |
| Dependency: Database | [connection test] | DB is reachable and responsive | [e.g., every 30s] |
| Dependency: [Service] | [ping / API call] | External service is available | [e.g., every 60s] |
| Synthetic / Smoke | [e.g., run key user flow] | End-to-end path works | [e.g., every 5 min] |

## SLOs & Error Budgets
**What service level objectives do we commit to?**

| SLO | Target | Measurement window | Error budget |
|-----|--------|-------------------|-------------|
| Availability | [e.g., 99.9%] | [rolling 30 days] | [~43 min downtime/month] |
| Latency (p95) | [e.g., < 200ms] | [rolling 7 days] | [5% of requests can exceed] |
| Data durability | [e.g., no data loss] | [per incident] | [zero tolerance] |

- How do we track error budget consumption?
- What happens when the error budget is exhausted (freeze deploys, prioritize reliability)?
