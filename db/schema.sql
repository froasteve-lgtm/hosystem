-- Team handover system schema (PostgreSQL)

CREATE TABLE teams (
  id UUID PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
  id UUID PRIMARY KEY,
  team_id UUID REFERENCES teams(id),
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  role VARCHAR(40) NOT NULL CHECK (role IN ('operator', 'shift_lead', 'admin')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE shifts (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id),
  shift_name VARCHAR(80) NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE shift_reports (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id),
  shift_id UUID NOT NULL REFERENCES shifts(id),
  author_id UUID NOT NULL REFERENCES users(id),
  summary TEXT NOT NULL,
  incidents TEXT,
  blockers TEXT,
  metrics JSONB,
  status VARCHAR(30) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'acknowledged')),
  submitted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE handover_items (
  id UUID PRIMARY KEY,
  report_id UUID NOT NULL REFERENCES shift_reports(id) ON DELETE CASCADE,
  team_id UUID NOT NULL REFERENCES teams(id),
  title VARCHAR(200) NOT NULL,
  details TEXT,
  priority VARCHAR(20) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
  status VARCHAR(30) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'blocked', 'done')),
  owner_id UUID REFERENCES users(id),
  due_at TIMESTAMPTZ,
  created_by UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE handover_acknowledgements (
  id UUID PRIMARY KEY,
  report_id UUID NOT NULL REFERENCES shift_reports(id) ON DELETE CASCADE,
  acknowledged_by UUID NOT NULL REFERENCES users(id),
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(report_id, acknowledged_by)
);

CREATE TABLE report_events (
  id UUID PRIMARY KEY,
  report_id UUID NOT NULL REFERENCES shift_reports(id) ON DELETE CASCADE,
  actor_id UUID NOT NULL REFERENCES users(id),
  event_type VARCHAR(60) NOT NULL,
  event_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_shift_reports_team_shift ON shift_reports(team_id, shift_id);
CREATE INDEX idx_handover_items_team_status ON handover_items(team_id, status);
CREATE INDEX idx_handover_items_due_at ON handover_items(due_at);
CREATE INDEX idx_report_events_report_id ON report_events(report_id);
