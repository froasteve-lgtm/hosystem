# Team Handover System (Runnable MVP)

A runnable MVP for multiple teams to write shift reports and hand over work to the next shift.

## What you can do in this MVP

- Create teams.
- Create users (operator / shift lead / admin).
- Create a shift.
- Create a shift report.
- Create handover items.
- View team dashboard counts (open, overdue, critical open).
- View handover items list.

## Tech stack (this scaffold)

- **Backend:** Python standard library HTTP server
- **Database:** SQLite (file at `data/handover.db`)
- **Frontend:** Static HTML/CSS/JS
- **Runtime:** Local Python or Docker Compose

## Project structure

- `app.py` – API server + SQLite schema init + static file serving
- `public/` – MVP frontend UI
- `db/schema.sql` – original PostgreSQL draft schema (reference)
- `docker-compose.yml` – local runtime for app

## Quick start (local)

```bash
python app.py
```

Then open:

- UI: http://localhost:3000
- Health: http://localhost:3000/api/health

## Quick start (docker compose)

```bash
docker compose up
```

Then open http://localhost:3000

## API endpoints (implemented)

- `GET /api/health`
- `GET /api/teams`
- `POST /api/teams`
- `GET /api/users?teamId=...`
- `POST /api/users`
- `GET /api/shifts?teamId=...`
- `POST /api/shifts`
- `POST /api/shift-reports`
- `GET /api/shift-reports/:id`
- `POST /api/shift-reports/:id/handover-items`
- `PATCH /api/handover-items/:id`
- `GET /api/handover-items?teamId=...&status=open`
- `POST /api/shift-reports/:id/acknowledge`
- `GET /api/dashboard?teamId=...`

## Notes

- This is an MVP scaffold focused on end-to-end flow you can run immediately.
- Authentication and full RBAC are not enforced yet.
- Next step can be adding login, report history screens, and automated tests.
