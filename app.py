#!/usr/bin/env python3
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
DB_PATH = ROOT / 'data' / 'handover.db'
PUBLIC_DIR = ROOT / 'public'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute('PRAGMA foreign_keys = ON')

    con.executescript(
        '''
        CREATE TABLE IF NOT EXISTS teams (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY,
          team_id TEXT NOT NULL,
          full_name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          role TEXT NOT NULL CHECK (role IN ('operator', 'shift_lead', 'admin')),
          is_active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          FOREIGN KEY(team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS shifts (
          id TEXT PRIMARY KEY,
          team_id TEXT NOT NULL,
          shift_name TEXT NOT NULL,
          starts_at TEXT NOT NULL,
          ends_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(team_id) REFERENCES teams(id),
          FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS shift_reports (
          id TEXT PRIMARY KEY,
          team_id TEXT NOT NULL,
          shift_id TEXT NOT NULL,
          author_id TEXT NOT NULL,
          summary TEXT NOT NULL,
          incidents TEXT,
          blockers TEXT,
          metrics TEXT,
          status TEXT NOT NULL CHECK (status IN ('draft', 'submitted', 'acknowledged')),
          submitted_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(team_id) REFERENCES teams(id),
          FOREIGN KEY(shift_id) REFERENCES shifts(id),
          FOREIGN KEY(author_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS handover_items (
          id TEXT PRIMARY KEY,
          report_id TEXT NOT NULL,
          team_id TEXT NOT NULL,
          title TEXT NOT NULL,
          details TEXT,
          priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
          status TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'blocked', 'done')),
          owner_id TEXT,
          due_at TEXT,
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(report_id) REFERENCES shift_reports(id) ON DELETE CASCADE,
          FOREIGN KEY(team_id) REFERENCES teams(id),
          FOREIGN KEY(owner_id) REFERENCES users(id),
          FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS handover_acknowledgements (
          id TEXT PRIMARY KEY,
          report_id TEXT NOT NULL,
          acknowledged_by TEXT NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL,
          UNIQUE(report_id, acknowledged_by),
          FOREIGN KEY(report_id) REFERENCES shift_reports(id) ON DELETE CASCADE,
          FOREIGN KEY(acknowledged_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS report_events (
          id TEXT PRIMARY KEY,
          report_id TEXT NOT NULL,
          actor_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          event_payload TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(report_id) REFERENCES shift_reports(id) ON DELETE CASCADE,
          FOREIGN KEY(actor_id) REFERENCES users(id)
        );
        '''
    )
    con.commit()
    con.close()


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con


class Handler(BaseHTTPRequestHandler):
    def _read_json(self):
        size = int(self.headers.get('Content-Length', 0))
        if size == 0:
            return {}
        raw = self.rfile.read(size)
        return json.loads(raw.decode('utf-8'))

    def _send_json(self, code, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath):
        if not filepath.exists() or not filepath.is_file():
            self.send_error(404)
            return
        content = filepath.read_bytes()
        if filepath.suffix == '.html':
            ctype = 'text/html; charset=utf-8'
        elif filepath.suffix == '.css':
            ctype = 'text/css; charset=utf-8'
        elif filepath.suffix == '.js':
            ctype = 'application/javascript; charset=utf-8'
        else:
            ctype = 'application/octet-stream'
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _event(self, con, report_id, actor_id, event_type, payload):
        con.execute(
            'INSERT INTO report_events (id, report_id, actor_id, event_type, event_payload, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (str(uuid.uuid4()), report_id, actor_id, event_type, json.dumps(payload), now_iso()),
        )

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == '/' or path == '/index.html':
            return self._send_file(PUBLIC_DIR / 'index.html')
        if path.startswith('/public/'):
            rel = path.replace('/public/', '')
            return self._send_file(PUBLIC_DIR / rel)
        if path in ['/styles.css', '/app.js']:
            return self._send_file(PUBLIC_DIR / path[1:])

        con = db()
        try:
            if path == '/api/health':
                return self._send_json(200, {'ok': True})

            if path == '/api/teams':
                rows = [dict(r) for r in con.execute('SELECT * FROM teams ORDER BY created_at DESC').fetchall()]
                return self._send_json(200, rows)

            if path == '/api/users':
                if 'teamId' in qs:
                    rows = [dict(r) for r in con.execute('SELECT * FROM users WHERE team_id = ? ORDER BY created_at DESC', (qs['teamId'][0],)).fetchall()]
                else:
                    rows = [dict(r) for r in con.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()]
                return self._send_json(200, rows)

            if path == '/api/shifts':
                if 'teamId' in qs:
                    rows = [dict(r) for r in con.execute('SELECT * FROM shifts WHERE team_id = ? ORDER BY starts_at DESC', (qs['teamId'][0],)).fetchall()]
                else:
                    rows = [dict(r) for r in con.execute('SELECT * FROM shifts ORDER BY starts_at DESC').fetchall()]
                return self._send_json(200, rows)

            if path == '/api/handover-items':
                sql = 'SELECT * FROM handover_items WHERE 1=1'
                params = []
                if 'teamId' in qs:
                    sql += ' AND team_id = ?'
                    params.append(qs['teamId'][0])
                if 'status' in qs:
                    sql += ' AND status = ?'
                    params.append(qs['status'][0])
                sql += ' ORDER BY created_at DESC'
                rows = [dict(r) for r in con.execute(sql, params).fetchall()]
                return self._send_json(200, rows)

            if path == '/api/dashboard':
                team_id = qs.get('teamId', [None])[0]
                if not team_id:
                    return self._send_json(400, {'error': 'teamId is required'})
                open_count = con.execute(
                    "SELECT COUNT(*) c FROM handover_items WHERE team_id = ? AND status IN ('open','in_progress','blocked')",
                    (team_id,),
                ).fetchone()['c']
                overdue_count = con.execute(
                    "SELECT COUNT(*) c FROM handover_items WHERE team_id = ? AND status IN ('open','in_progress','blocked') AND due_at IS NOT NULL AND due_at < ?",
                    (team_id, now_iso()),
                ).fetchone()['c']
                critical_count = con.execute(
                    "SELECT COUNT(*) c FROM handover_items WHERE team_id = ? AND status IN ('open','in_progress','blocked') AND priority = 'critical'",
                    (team_id,),
                ).fetchone()['c']
                return self._send_json(200, {
                    'open_items': open_count,
                    'overdue_items': overdue_count,
                    'critical_open_items': critical_count,
                })

            if path.startswith('/api/shift-reports/'):
                report_id = path.split('/')[-1]
                report = con.execute('SELECT * FROM shift_reports WHERE id = ?', (report_id,)).fetchone()
                if not report:
                    return self._send_json(404, {'error': 'not found'})
                items = [dict(r) for r in con.execute('SELECT * FROM handover_items WHERE report_id = ? ORDER BY created_at DESC', (report_id,)).fetchall()]
                events = [dict(r) for r in con.execute('SELECT * FROM report_events WHERE report_id = ? ORDER BY created_at DESC', (report_id,)).fetchall()]
                return self._send_json(200, {'report': dict(report), 'items': items, 'events': events})
        finally:
            con.close()

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self._read_json()
        con = db()
        try:
            if path == '/api/teams':
                if not data.get('name'):
                    return self._send_json(400, {'error': 'name is required'})
                row = {
                    'id': str(uuid.uuid4()),
                    'name': data['name'],
                    'created_at': now_iso(),
                }
                con.execute('INSERT INTO teams (id, name, created_at) VALUES (?, ?, ?)', (row['id'], row['name'], row['created_at']))
                con.commit()
                return self._send_json(201, row)

            if path == '/api/users':
                for key in ('team_id', 'full_name', 'email'):
                    if not data.get(key):
                        return self._send_json(400, {'error': f'{key} is required'})
                row = {
                    'id': str(uuid.uuid4()),
                    'team_id': data['team_id'],
                    'full_name': data['full_name'],
                    'email': data['email'],
                    'role': data.get('role', 'operator'),
                    'is_active': 1,
                    'created_at': now_iso(),
                }
                con.execute(
                    'INSERT INTO users (id, team_id, full_name, email, role, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (row['id'], row['team_id'], row['full_name'], row['email'], row['role'], row['is_active'], row['created_at']),
                )
                con.commit()
                return self._send_json(201, row)

            if path == '/api/shifts':
                for key in ('team_id', 'shift_name', 'starts_at', 'ends_at', 'created_by'):
                    if not data.get(key):
                        return self._send_json(400, {'error': f'{key} is required'})
                row = {
                    'id': str(uuid.uuid4()),
                    'team_id': data['team_id'],
                    'shift_name': data['shift_name'],
                    'starts_at': data['starts_at'],
                    'ends_at': data['ends_at'],
                    'created_by': data['created_by'],
                    'created_at': now_iso(),
                }
                con.execute(
                    'INSERT INTO shifts (id, team_id, shift_name, starts_at, ends_at, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (row['id'], row['team_id'], row['shift_name'], row['starts_at'], row['ends_at'], row['created_by'], row['created_at']),
                )
                con.commit()
                return self._send_json(201, row)

            if path == '/api/shift-reports':
                for key in ('team_id', 'shift_id', 'author_id', 'summary'):
                    if not data.get(key):
                        return self._send_json(400, {'error': f'{key} is required'})
                row = {
                    'id': str(uuid.uuid4()),
                    'team_id': data['team_id'],
                    'shift_id': data['shift_id'],
                    'author_id': data['author_id'],
                    'summary': data['summary'],
                    'incidents': data.get('incidents'),
                    'blockers': data.get('blockers'),
                    'metrics': json.dumps(data.get('metrics', {})),
                    'status': data.get('status', 'submitted'),
                    'submitted_at': now_iso(),
                    'created_at': now_iso(),
                    'updated_at': now_iso(),
                }
                con.execute(
                    'INSERT INTO shift_reports (id, team_id, shift_id, author_id, summary, incidents, blockers, metrics, status, submitted_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        row['id'], row['team_id'], row['shift_id'], row['author_id'], row['summary'], row['incidents'], row['blockers'],
                        row['metrics'], row['status'], row['submitted_at'], row['created_at'], row['updated_at'],
                    ),
                )
                self._event(con, row['id'], row['author_id'], 'report_created', {'status': row['status']})
                con.commit()
                return self._send_json(201, row)

            if path.endswith('/handover-items') and path.startswith('/api/shift-reports/'):
                report_id = path.split('/')[-2]
                for key in ('team_id', 'title', 'created_by'):
                    if not data.get(key):
                        return self._send_json(400, {'error': f'{key} is required'})
                row = {
                    'id': str(uuid.uuid4()),
                    'report_id': report_id,
                    'team_id': data['team_id'],
                    'title': data['title'],
                    'details': data.get('details'),
                    'priority': data.get('priority', 'medium'),
                    'status': 'open',
                    'owner_id': data.get('owner_id'),
                    'due_at': data.get('due_at'),
                    'created_by': data['created_by'],
                    'created_at': now_iso(),
                    'updated_at': now_iso(),
                }
                con.execute(
                    'INSERT INTO handover_items (id, report_id, team_id, title, details, priority, status, owner_id, due_at, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        row['id'], row['report_id'], row['team_id'], row['title'], row['details'], row['priority'], row['status'],
                        row['owner_id'], row['due_at'], row['created_by'], row['created_at'], row['updated_at'],
                    ),
                )
                self._event(con, report_id, row['created_by'], 'handover_item_created', {'item_id': row['id'], 'title': row['title']})
                con.commit()
                return self._send_json(201, row)

            if path.endswith('/acknowledge') and path.startswith('/api/shift-reports/'):
                report_id = path.split('/')[-2]
                if not data.get('acknowledged_by'):
                    return self._send_json(400, {'error': 'acknowledged_by is required'})
                con.execute(
                    'INSERT OR IGNORE INTO handover_acknowledgements (id, report_id, acknowledged_by, note, created_at) VALUES (?, ?, ?, ?, ?)',
                    (str(uuid.uuid4()), report_id, data['acknowledged_by'], data.get('note'), now_iso()),
                )
                con.execute('UPDATE shift_reports SET status = ?, updated_at = ? WHERE id = ?', ('acknowledged', now_iso(), report_id))
                self._event(con, report_id, data['acknowledged_by'], 'report_acknowledged', {'note': data.get('note')})
                con.commit()
                return self._send_json(200, {'ok': True})
        except sqlite3.IntegrityError as ex:
            return self._send_json(400, {'error': 'integrity_error', 'detail': str(ex)})
        finally:
            con.close()

        self.send_error(404)

    def do_PATCH(self):
        path = urlparse(self.path).path
        if not path.startswith('/api/handover-items/'):
            return self.send_error(404)

        item_id = path.split('/')[-1]
        data = self._read_json()

        con = db()
        try:
            row = con.execute('SELECT * FROM handover_items WHERE id = ?', (item_id,)).fetchone()
            if not row:
                return self._send_json(404, {'error': 'not found'})

            status = data.get('status', row['status'])
            owner_id = data['owner_id'] if 'owner_id' in data else row['owner_id']
            due_at = data['due_at'] if 'due_at' in data else row['due_at']
            updated_at = now_iso()

            con.execute(
                'UPDATE handover_items SET status = ?, owner_id = ?, due_at = ?, updated_at = ? WHERE id = ?',
                (status, owner_id, due_at, updated_at, item_id),
            )
            actor_id = data.get('actor_id')
            if actor_id:
                self._event(con, row['report_id'], actor_id, 'handover_item_updated', {'item_id': item_id, 'status': status})
            con.commit()

            updated = dict(con.execute('SELECT * FROM handover_items WHERE id = ?', (item_id,)).fetchone())
            return self._send_json(200, updated)
        finally:
            con.close()


def run():
    init_db()
    port = int(os.environ.get('PORT', '3000'))
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'Handover MVP running at http://localhost:{port}')
    server.serve_forever()


if __name__ == '__main__':
    run()
