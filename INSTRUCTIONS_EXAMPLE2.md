# Redmine Environment Instructions

This document contains key information about the Redmine environment structure to help with future issue management and API interactions.

## Project Structure

- **Default Project**: Operations (ID: 1, identifier: "ops")
- **Project Status**: Active (Status ID: 1)
- **Project Visibility**: Public
- **Created**: March 15, 2025
- **Last Updated**: March 18, 2025

## Team Members & Roles

All members have Manager role (Role ID: 3):

1. **Alex Wilson** (ID: 5)
2. **Morgan Chen** (ID: 6)
3. **Taylor Roberts** (ID: 7)
4. **Jordan Bailey** (ID: 8)

## Issue Categories

1. **Task - Technical** (ID: 1)
2. **Task - Advisory** (ID: 2)
3. **Deployment** (ID: 3)
4. **Task - Customer** (ID: 4)
5. **Task - Portal** (ID: 5)
6. **DEV** (ID: 6)

## Available Trackers

1. **Code** (ID: 1) - Default tracker
2. **Feature** (ID: 2)
3. **Support** (ID: 3)

## Issue Statuses

Status IDs identified in the system:
1. **New** (ID: 1, is_closed: true)
2. **In Progress** (ID: 2)
3. **Feedback** (ID: 4)
4. **Done** (ID: 5, is_closed: true)
5. **Cancelled** (ID: 6, is_closed: true)
6. **Backlog** (ID: 7, is_closed: true)
7. **Pipelined** (ID: 8)

## Custom Fields

1. **Pull Request Reviewers** (ID: 2, multiple: true)
2. **Pull Request Targeted Branches** (ID: 3, multiple: true)

## API Usage Notes

- When creating or updating issues, the default tracker is "Code" (ID: 1)
- All issues in the Operations project should have a category assigned
- Work Units (WU) are calculated at 8 hours (1 day) per unit
- Estimated hours should be set in hours (WU × 8)
- In Redmine, start_date and due_date format is "YYYY-MM-DD"

## Pull Request Integration

This does not give any useful information, please ignore.

## Common API Endpoints

- `/projects/ops.json` - Project details
- `/projects/ops/memberships.json` - Project members
- `/projects/ops/issue_categories.json` - Issue categories
- `/trackers.json` - Available trackers
- `/issues.json?project_id=ops` - Issues for Operations project
- `/issues/{issue_id}.json` - Specific issue details
