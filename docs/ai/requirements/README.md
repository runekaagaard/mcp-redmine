---
phase: requirements
title: Requirements & Problem Understanding
description: Clarify the problem space, gather requirements, and define success criteria
template_usage: Copy this file to feature-{name}.md and fill in each section
created_at: {{datetime}}
updated_at: {{datetime}}
---

# Requirements & Problem Understanding

> **Template**: Copy to `feature-{name}.md` before editing. Run `/review-requirements` to validate.
>
> **Prerequisite**: For new features, the brainstorming skill (`cxl-brainstorming`) steps 1-4 feed directly into this document. The Understanding Lock summary maps to Problem Statement + Goals + Non-Goals, and brainstorming NFRs map to Success Criteria.

**Related docs**: [Design](../design/) | [Planning](../planning/) | [Implementation](../implementation/) | [Testing](../testing/)
**Applicable rules/skills**: `cxl-brainstorming` (steps 1-4)

## Problem Statement
**What problem are we solving?**

- What is the core problem or pain point?
- Who is affected (user types, teams, systems)?
- What is the current situation or workaround?
- What is the cost of not solving this (user friction, revenue, tech debt)?

## Stakeholders
**Who needs to be involved?**

- Decision makers and approvers
- Subject-matter experts to consult
- Downstream teams or systems affected

## Goals & Objectives
**What do we want to achieve?**

- Primary goals (must achieve for the feature to ship)
- Secondary goals (valuable but deferrable)

## Non-Goals & Scope Boundaries
**What is explicitly out of scope?**

- Features or behaviors we are intentionally not building
- Adjacent problems we are not solving in this iteration
- Known requests being deferred and why

## User Stories & Use Cases
**How will users interact with the solution?**

List at least one story per user type. Include both happy paths and failure/edge cases.

| Priority | User type | Story | Notes |
|----------|-----------|-------|-------|
| P0 | [user type] | As a [user type], I want to [action] so that [benefit] | |
| P1 | [user type] | As a [user type], I want to [action] so that [benefit] | |
| P2 | [user type] | As a [user type], I want to [action] so that [benefit] | |

- Key workflows and scenarios
- Unhappy paths and edge cases (invalid input, permissions, concurrency, empty states)

## Success Criteria
**How will we know when we're done?**

Define measurable criteria that the testing phase can verify.

| Criteria | Target | How to measure |
|----------|--------|----------------|
| [What] | [Threshold or behavior] | [Method: test, metric, manual check] |
| [What] | [Threshold or behavior] | [Method] |

## Non-Functional Requirements
**What quality attributes matter? (mandatory per brainstorming skill step 3)**

Explicitly clarify or propose assumptions for each. If unsure, state reasonable defaults and mark as assumptions.

- **Performance**: What response times or throughput are acceptable?
- **Scale**: How many users, records, or requests must be supported?
- **Security/Privacy**: What data protection, compliance, or access control is required?
- **Reliability/Availability**: What uptime target? What happens during downtime?
- **Maintenance**: Who owns this long-term? What is the expected support burden?

## Constraints & Assumptions
**What limitations do we need to work within?**

- What technologies, versions, or platforms are we locked into?
- What compliance, regulatory, or policy requirements apply?
- What time or budget boundaries exist?
- What are we assuming to be true (and what would invalidate those assumptions)?

## Dependencies
**What external factors does this feature rely on?**

- APIs, services, or systems that must be available
- Data sources or migrations required
- Other features or teams that must deliver first

## Questions & Open Items
**What do we still need to clarify?**

- Unresolved questions (with owner and target date if known)
- Items requiring stakeholder input
- Research or spikes needed before committing to a direction
