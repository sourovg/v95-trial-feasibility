"""Local SQLite store for feasibility projects, survey invitations and responses."""
import json
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("COHORTIA_DB", os.path.join(ROOT, "data", "cohortia.db"))
_lock = threading.Lock()


def _conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript("""
    create table if not exists projects(id text primary key, created text, req text, questions text, settings text);
    create table if not exists invites(token text primary key, project_id text, site text, status text, sent_at text);
    create table if not exists responses(token text primary key, project_id text, answers text, created text, synthetic integer);
    """)
    return c


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def create_project(req, questions):
    pid = "FR-" + secrets.token_hex(3).upper()
    with _lock, _conn() as c:
        c.execute("insert into projects values(?,?,?,?,?)", (pid, now(), json.dumps(req), json.dumps(questions), "{}"))
    return pid


def get_project(pid):
    with _conn() as c:
        r = c.execute("select * from projects where id=?", (pid,)).fetchone()
    if not r:
        return None
    return {"id": r["id"], "created": r["created"], "req": json.loads(r["req"]), "questions": json.loads(r["questions"]), "settings": json.loads(r["settings"] or "{}")}


def list_projects(limit=12):
    with _conn() as c:
        rows = c.execute("select id, created, req from projects order by created desc limit ?", (limit,)).fetchall()
    return [{"id": r["id"], "created": r["created"], "req": json.loads(r["req"])} for r in rows]


def update_settings(pid, settings):
    with _lock, _conn() as c:
        c.execute("update projects set settings=? where id=?", (json.dumps(settings), pid))


def update_questions(pid, questions):
    with _lock, _conn() as c:
        c.execute("update projects set questions=? where id=?", (json.dumps(questions), pid))


def add_invites(pid, sites):
    toks = []
    with _lock, _conn() as c:
        have = {json.loads(r["site"])["key"] for r in c.execute("select site from invites where project_id=?", (pid,))}
        for s in sites:
            if s["key"] in have:
                continue
            t = secrets.token_urlsafe(9)
            c.execute("insert into invites values(?,?,?,?,?)", (t, pid, json.dumps(s), "draft", None))
            toks.append(t)
    return toks


def invites(pid):
    with _conn() as c:
        rows = c.execute("select i.*, r.answers, r.synthetic, r.created as answered from invites i left join responses r on r.token=i.token where i.project_id=? order by i.rowid", (pid,)).fetchall()
    return [{"token": r["token"], "site": json.loads(r["site"]), "status": r["status"], "sent_at": r["sent_at"],
             "answers": json.loads(r["answers"]) if r["answers"] else None, "synthetic": bool(r["synthetic"]), "answered": r["answered"]} for r in rows]


def mark_sent(pid):
    with _lock, _conn() as c:
        c.execute("update invites set status='sent (simulated)', sent_at=? where project_id=? and status='draft'", (now(), pid))


def invite(token):
    with _conn() as c:
        r = c.execute("select * from invites where token=?", (token,)).fetchone()
    return None if not r else {"token": r["token"], "project_id": r["project_id"], "site": json.loads(r["site"]), "status": r["status"]}


def save_response(token, pid, answers, synthetic=False):
    with _lock, _conn() as c:
        c.execute("insert or replace into responses values(?,?,?,?,?)", (token, pid, json.dumps(answers), now(), 1 if synthetic else 0))
        c.execute("update invites set status='completed' where token=?", (token,))


def clear_synthetic(pid):
    with _lock, _conn() as c:
        toks = [r["token"] for r in c.execute("select token from responses where project_id=? and synthetic=1", (pid,))]
        c.execute("delete from responses where project_id=? and synthetic=1", (pid,))
        for t in toks:
            c.execute("update invites set status='sent (simulated)' where token=?", (t,))
