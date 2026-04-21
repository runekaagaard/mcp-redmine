---
phase: testing
title: Testing Strategy
description: Define testing approach, test cases, and quality assurance
template_usage: Copy this file to feature-{name}.md and fill in each section
created_at: {{datetime}}
updated_at: {{datetime}}
---

# Testing Strategy

> **Template**: Copy to `feature-{name}.md` before editing. Run `/write-tests` to generate tests.

**Related docs**: [Requirements](../requirements/) | [Design](../design/) | [Planning](../planning/) | [Implementation](../implementation/)
**Applicable rules/skills**: `cxl-coding-standards` (AAA pattern, test naming), `cxl-security-review` (security testing) and AI Model Auto Decision Making

## Test Coverage Goals
**What level of testing do we aim for?**

| Test level | Scope | Coverage target |
|-----------|-------|----------------|
| Unit | Individual functions, methods, components | 100% of new/changed code |
| Integration | Cross-component flows, API contracts, DB queries | Critical paths + error handling |
| End-to-end | Full user journeys through the system | Key user stories from requirements |

- How do coverage targets align with the success criteria in the requirements doc?
- What is the minimum coverage gate for merging (e.g., no PR merges below 90%)?

## Test Conventions (from `cxl-coding-standards`)

### Structure: AAA Pattern
All tests should follow **Arrange-Act-Assert**:
```
// Arrange — set up test data and conditions
// Act — execute the function/behavior under test
// Assert — verify the expected outcome
```

### Naming
Use descriptive names that explain the scenario:
- `returns empty array when no markets match query`
- `throws error when API key is missing`
- `falls back to substring search when Redis unavailable`

Avoid vague names like `works`, `test search`, or `handles data`.

## Unit Tests
**What individual components need testing?**

For each module, list the behaviors to verify. Map back to requirements user stories where applicable.

### [Component/Module 1]

| Test case | Scenario | Expected result | Priority | Status |
|-----------|----------|----------------|----------|--------|
| [Name] | Happy path: [description] | [Expected output/behavior] | P0 | [ ] |
| [Name] | Edge case: [description] | [Expected output/behavior] | P1 | [ ] |
| [Name] | Error: [description] | [Expected error/fallback] | P0 | [ ] |

### [Component/Module 2]

| Test case | Scenario | Expected result | Priority | Status |
|-----------|----------|----------------|----------|--------|
| [Name] | [description] | [Expected output/behavior] | P0 | [ ] |

## Integration Tests
**How do we test component interactions?**

| Scenario | Components involved | Setup/teardown | Expected behavior | Status |
|----------|-------------------|----------------|-------------------|--------|
| [Happy path flow] | [A -> B -> C] | [Fixtures, mocks, DB state] | [End-to-end result] | [ ] |
| [Failure mode] | [A -> B (fails)] | [Inject failure] | [Graceful degradation / rollback] | [ ] |
| [API contract] | [Client -> API] | [Auth token, test data] | [Correct response shape + status] | [ ] |

## End-to-End Tests
**What user flows need validation?**

Map each test to a user story from the requirements doc.

| User story ref | Flow description | Steps | Expected outcome | Status |
|---------------|-----------------|-------|-----------------|--------|
| [US-1] | [Description] | [Step-by-step] | [What user sees/gets] | [ ] |
| [US-2] | [Description] | [Step-by-step] | [What user sees/gets] | [ ] |

- What regression tests are needed for adjacent features that might break?
- What browsers/devices/environments must pass?

## Test Data
**What data do we use for testing?**

- What fixtures and mocks exist and where are they located?
- What seed data is required and how is it set up (scripts, factories, SQL)?
- How do we reset test state between runs (truncate, transactions, containers)?
- Are there any PII or sensitive data concerns in test data?

## Test Reporting & Coverage
**How do we verify and communicate test results?**

- What command produces the coverage report?
  ```bash
  # Example: npm run test -- --coverage
  ```
- What is the current coverage and where are the gaps?

| File / Module | Current coverage | Target | Gap reason |
|--------------|-----------------|--------|------------|
| [file] | [%] | 100% | [Why it's below target or acceptable] |

- Where are test reports published (CI dashboard, link)?
- Who signs off on manual testing outcomes?

## Manual Testing
**What requires human validation?**

- [ ] UI/UX testing: does the interface match design specs?
- [ ] Accessibility: keyboard navigation, screen reader, color contrast
- [ ] Browser/device compatibility: [list target browsers and devices]
- [ ] Smoke tests after deployment: [list critical checks]
- [ ] Destructive testing: what happens with unexpected input, rapid clicks, network loss?

## Performance Testing
**How do we validate performance targets from the design doc?**

| Scenario | Tool | Target | Baseline | Status |
|----------|------|--------|----------|--------|
| [Load test: N concurrent users] | [k6/Artillery/etc.] | [p95 < Xms] | [Current measurement] | [ ] |
| [Stress test: peak traffic] | [tool] | [No errors up to N rps] | [Current] | [ ] |
| [Specific operation benchmark] | [tool] | [< Xms] | [Current] | [ ] |

## Security Testing (from `cxl-security-review`)
**What security-specific tests are needed?**

Reference the `cxl-security-review` skill for the full checklist. Automate these where possible:

- [ ] Authentication: unauthenticated requests return 401
- [ ] Authorization: unauthorized role returns 403
- [ ] Input validation: malformed/malicious input returns 400 (not 500)
- [ ] Rate limiting: excessive requests return 429
- [ ] SQL injection: parameterized queries resist injection payloads
- [ ] XSS: user-provided content is sanitized before rendering
- [ ] Secrets: no hardcoded tokens or credentials in source or test data
- [ ] Sensitive data: error responses don't leak stack traces or internal details

## Known Issues & Deferred Tests
**What testing gaps exist and why?**

| Gap | Reason deferred | Risk if untested | Follow-up ticket |
|-----|----------------|-----------------|-----------------|
| [What's not tested] | [Why: time, environment, tooling] | [What could go wrong] | [Link or ID] |

