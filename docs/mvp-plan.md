# MVP backlog and implementation status

## Implemented in this scaffold

- Runnable app (`python app.py`) with browser UI.
- Optional Docker Compose runtime.
- CRUD basics for teams and users.
- Shift creation.
- Shift report creation and fetch by ID.
- Handover item creation and status update endpoint.
- Dashboard summary endpoint for open/overdue/critical items.
- Simple web UI to create records and view dashboard/items.

## Remaining must-have

- Authentication and RBAC enforcement.
- Incoming shift acknowledgement UI flow.
- Shift history page with filters.
- Better validation and user-friendly errors.

## Nice-to-have

- Attachments for incidents.
- @mentions and comments on handover items.
- Notification channels (email/Slack/Teams).
- Export reports to PDF/CSV.

## Acceptance criteria examples

1. A shift lead can submit one report per team shift period.
2. Incoming shift can acknowledge a submitted report.
3. Open critical handover items appear on dashboard quickly.
4. All status changes appear in report events audit history.
