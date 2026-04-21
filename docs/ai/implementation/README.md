---
phase: implementation
title: Implementation Guide
description: Technical implementation notes, patterns, and code guidelines
template_usage: Copy this file to feature-{name}.md and fill in each section
created_at: {{datetime}}
updated_at: {{datetime}}
---

# Implementation Guide

> **Template**: Copy to `feature-{name}.md` before editing. Run `/check-implementation` to verify alignment with design.

**Related docs**: [Requirements](../requirements/) | [Design](../design/) | [Planning](../planning/) | [Testing](../testing/)
**Applicable rules/skills**: `2-dotenv-environments` (env config), `3-coding-style`, `cxl-coding-standards` (patterns), `cxl-security-review` (security checklist) and AI Model Auto Decision Making

## Development Setup
**How do we get started?**

Provide copy-pasteable setup instructions so a new contributor can go from clone to running in minutes.

- What language/runtime versions are required (e.g., Node 20, Python 3.12)?
- What system-level dependencies must be installed (e.g., Docker, Postgres, Redis)?
- What are the exact setup commands?
  ```bash
  # Example:
  # cp .env.example .env
  # npm install
  # npm run dev
  ```

### Environment Configuration (per `2-dotenv-environments` rule)

Follow the project's .env file structure:

```
.env.example      # Template with all variables (committed, no real secrets)
.env              # Local development overrides (gitignored)
.env.development  # Development defaults
.env.staging      # Staging environment
.env.production   # Production environment
```

- What environment variables are required? List them all in `.env.example` with placeholder values.
- Are required variables validated at application startup? (They should be.)
- Where do real values come from for each environment (secrets manager, team vault, hosting platform)?

## Code Structure
**How is the code organized?**

Per the `3-coding-style` rule: organize by feature/domain (not by type), keep files 200-400 lines (800 max), and extract utilities from large components.

```
project-root/
├── src/           # [describe purpose]
│   ├── modules/   # [describe purpose — organized by feature/domain]
│   └── shared/    # [describe purpose]
├── tests/         # [describe purpose]
└── config/        # [describe purpose]
```

- What naming conventions do we follow (files, functions, classes, database tables)?
- Where does new feature code go?
- What shared utilities/helpers exist and where?
- What is the maximum acceptable file size for this project?

## Implementation Notes
**Key technical details and decisions made during development.**

Record anything a future reader would need to understand *why* the code is written the way it is.

| Feature / Area | Approach | Why this way | Caveats |
|---------------|----------|-------------|---------|
| [Feature 1] | [How it's implemented] | [Rationale] | [Gotchas or limitations] |
| [Feature 2] | [How it's implemented] | [Rationale] | [Gotchas or limitations] |

### Patterns & Best Practices
Per `cxl-coding-standards`: apply KISS, DRY, and YAGNI. Prefer readability over cleverness.

- What design patterns are we using and where (e.g., repository pattern for data access)?
- What code style rules go beyond the linter (e.g., prefer composition over inheritance)?
- Are immutable patterns used for state updates (spread operator, not direct mutation)?
- What common mistakes should be avoided?

## Integration Points
**How do pieces connect?**

| Integration | Protocol | Auth | Error handling | Docs/Contract |
|------------|----------|------|---------------|---------------|
| [API name / service] | [REST/gRPC/queue] | [API key/JWT/etc.] | [Retry? Circuit breaker?] | [Link to spec] |
| [Database] | [Driver/ORM] | [Connection string source] | [Pool config, timeouts] | |
| [Third-party service] | [SDK/API] | [How authenticated] | [What if it's down?] | [Link] |

## Error Handling
**How do we handle failures?**

- What is the error hierarchy (custom error classes, error codes)?
- How are errors surfaced to users vs logged internally?
- What retry/fallback strategies are in place and for which operations?
- How do we avoid swallowing errors silently?
- What structured logging format do we use (fields, levels, correlation IDs)?

## Performance Considerations
**How do we keep it fast?**

- What are the known hot paths and how are they optimized?
- What caching is in place (layer, TTL, invalidation strategy)?
- What database query optimizations matter (indexes, query plans, N+1 prevention)?
- What resource limits are configured (connection pools, memory caps, timeouts)?
- What should be profiled or benchmarked before shipping?

## Security Notes
**What security measures are in place?**

Reference the `cxl-security-review` skill for the full checklist. Key areas to document:

- How is authentication implemented (session, JWT with httpOnly cookies — not localStorage)?
- How is authorization enforced (roles, permissions, row-level security)?
- Where is user input validated and sanitized (use schema validation like Zod)?
- Are all database queries parameterized (no string concatenation in SQL)?
- What data is encrypted at rest and in transit?
- How are secrets managed (env vars per `2-dotenv-environments` rule, never hardcoded)?
- Is rate limiting configured on all API endpoints?
- Are CSP headers and CSRF protection in place?
- What security-relevant dependencies should be kept up to date (`npm audit`)?

## Migration Notes
**What data or schema changes does this feature introduce?**

- What migrations are required and in what order?
- Are the migrations reversible?
- Is there a data backfill needed for existing records?
- What is the expected migration duration for production data volumes?

## Knowledge Docs
**Documented code entry points and deep dives.**

Use `/capture-knowledge` to analyze a code entry point and generate a structured doc at `knowledge-{name}.md` in this directory. These files capture purpose, execution flow, dependencies, and mermaid diagrams for key areas of the codebase.
