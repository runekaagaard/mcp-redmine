# Thanks to github user dkd-dobberkau

## Custom Instructions for Redmine API Usage

### Useful Tips
- When creating issues, always check the project ID first
- For date parameters, use ISO format: YYYY-MM-DD
- Status IDs: 1=New, 2=In Progress, 3=Resolved, 5=Closed
- Priority IDs: 1=Low, 2=Normal, 3=High, 4=Urgent, 5=Immediate

### Common Query Parameters
- offset: Pagination offset (default: 0)
- limit: Number of items to return (default: 25, max: 100)
- sort: Field to sort by (e.g., 'id:desc', 'priority:asc')

### Example Queries
- Get all open issues: `/issues.json?status_id=open`
- Get high priority issues: `/issues.json?priority_id=>=3`
- Find issues by text: `/issues.json?subject=~search_term`
- Get issues assigned to me: `/issues.json?assigned_to_id=me`

### Time Entry Format
- hours: Decimal number of hours (e.g., 1.5)
- activity_id: Activity type ID
- comments: Optional description of work done

### Issue Creation Fields
- project_id: (required) ID or identifier of the project
- subject: (required) Issue title
- description: Detailed description, supports Markdown
- priority_id: Issue priority (1-5)
- assigned_to_id: User ID to assign the issue to
- parent_issue_id: ID of parent issue for subtasks
- start_date/due_date: Format YYYY-MM-DD
- estimated_hours: Estimated time in decimal hours
