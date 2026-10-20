from datetime import date

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import IntegrityErrors, get_db
from .util import to_int

bp = Blueprint("trainer", __name__, url_prefix="/trainer")
RATINGS = ("good", "average", "poor")


def my_member(db, member_id):
    return db.execute("SELECT * FROM users WHERE id=? AND role='member' AND trainer_id=?",
                      (member_id, g.user["id"])).fetchone()


@bp.get("/")
@login_required("trainer")
def index():
    db = get_db()
    members = db.execute(
        "SELECT u.*, p.name AS plan_name, "
        "(SELECT COUNT(*) FROM progress WHERE member_id=u.id) AS logs, "
        "(SELECT MAX(log_date) FROM progress WHERE member_id=u.id) AS last_log "
        "FROM users u LEFT JOIN plans p ON p.id=u.plan_id "
        "WHERE u.role='member' AND u.trainer_id=? ORDER BY u.name", (g.user["id"],)).fetchall()
    equipment = db.execute("SELECT * FROM equipment ORDER BY name").fetchall()
    stats = {"members": len(members), "logs": sum(m["logs"] for m in members),
             "active": sum(1 for m in members if m["membership_end"] >= date.today().isoformat())}
    return render_template("trainer.html", members=members, equipment=equipment, ratings=RATINGS, stats=stats)


@bp.post("/log")
@login_required("trainer")
def log():
    f, db = request.form, get_db()
    member = my_member(db, to_int(f.get("member_id"), 0, 1, 10**9))
    note, rating = f.get("note", "").strip(), f.get("rating")
    try:
        day = date.fromisoformat(f.get("log_date", ""))
    except ValueError:
        day = None
    if not member or rating not in RATINGS or not note or day is None:
        flash("Pilih member Anda, tanggal yang valid, hasil, dan isi catatan.", "error")
    elif day > date.today():
        flash("Tanggal tidak boleh di masa depan.", "error")
    else:
        db.execute("INSERT INTO progress (member_id,log_date,rating,note) VALUES (?,?,?,?) "
                   "ON CONFLICT(member_id,log_date) DO UPDATE SET rating=excluded.rating, note=excluded.note",
                   (member["id"], day.isoformat(), rating, note))
        db.commit()
        flash(f"Progres {member['name']} tanggal {day} disimpan.", "ok")
    return redirect(url_for("trainer.index"))


@bp.get("/plans")
@login_required("trainer")
def plans():
    db = get_db()
    plans = db.execute("SELECT * FROM plans ORDER BY name").fetchall()
    exercises = {p["id"]: db.execute("SELECT * FROM plan_exercises WHERE plan_id=? ORDER BY id",
                                     (p["id"],)).fetchall() for p in plans}
    members = db.execute("SELECT * FROM users WHERE role='member' AND trainer_id=? ORDER BY name",
                         (g.user["id"],)).fetchall()
    return render_template("plans.html", plans=plans, exercises=exercises, members=members)


@bp.post("/plans")
@login_required("trainer")
def add_plan():
    name, db = request.form.get("name", "").strip(), get_db()
    try:
        if not name:
            raise ValueError
        db.execute("INSERT INTO plans (name) VALUES (?)", (name,))
        db.commit()
        flash(f"Rencana {name} dibuat. Tambahkan latihannya.", "ok")
    except (*IntegrityErrors, ValueError):
        db.rollback()
        flash("Nama rencana kosong atau sudah ada.", "error")
    return redirect(url_for("trainer.plans"))


@bp.post("/plans/<int:pid>/exercises")
@login_required("trainer")
def add_exercise(pid):
    f, db = request.form, get_db()
    try:
        exercise = f["exercise"].strip()
        sets, reps = to_int(f.get("sets"), 0, 0, 1000), to_int(f.get("reps"), 0, 0, 1000)
        if not exercise:
            raise ValueError
        db.execute("INSERT INTO plan_exercises (plan_id,exercise,sets,reps) VALUES (?,?,?,?)",
                   (pid, exercise, sets, reps))
        db.commit()
    except (KeyError, ValueError, *IntegrityErrors):
        db.rollback()
        flash("Isi latihan, set (1-20), dan repetisi (1-100).", "error")
    return redirect(url_for("trainer.plans"))


@bp.post("/members/<int:mid>/plan")
@login_required("trainer")
def assign_plan(mid):
    db = get_db()
    pid = to_int(request.form.get("plan_id"), 0, 0, 10**9)
    if my_member(db, mid) and db.execute("SELECT 1 FROM plans WHERE id=?", (pid,)).fetchone():
        db.execute("UPDATE users SET plan_id=? WHERE id=?", (pid, mid))
        db.commit()
        flash("Rencana latihan diterapkan.", "ok")
    else:
        flash("Member atau rencana tidak ditemukan.", "error")
    return redirect(url_for("trainer.plans"))
