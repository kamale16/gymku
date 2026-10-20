from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from .auth import login_required
from .db import IntegrityErrors, get_db
from .util import to_int

bp = Blueprint("admin", __name__, url_prefix="/admin")


def back(endpoint="admin.index"):
    return redirect(url_for(endpoint))


@bp.get("/")
@login_required("admin")
def index():
    db = get_db()
    users = db.execute(
        "SELECT u.*, t.name AS trainer_name, p.name AS plan_name FROM users u "
        "LEFT JOIN users t ON t.id=u.trainer_id LEFT JOIN plans p ON p.id=u.plan_id "
        "WHERE u.role!='admin' ORDER BY u.role, u.name").fetchall()
    trainers = [u for u in users if u["role"] == "trainer"]
    plans = db.execute("SELECT * FROM plans ORDER BY name").fetchall()
    members = [u for u in users if u["role"] == "member"]
    stats = {"members": len(members),
             "active": sum(1 for u in members if u["membership_end"] >= date.today().isoformat()),
             "equipment": db.execute("SELECT COALESCE(SUM(quantity),0) AS total FROM equipment").fetchone()["total"]}
    return render_template("admin.html", users=users, trainers=trainers, plans=plans, stats=stats)


@bp.post("/users")
@login_required("admin")
def add_user():
    f, db = request.form, get_db()
    role, username, name = f.get("role"), f.get("username", "").strip(), f.get("name", "").strip()
    if role not in ("trainer", "member") or not username or not name or len(f.get("password", "")) < 6:
        flash("Isi nama, username, peran, dan password (minimal 6 karakter).", "error")
        return back()
    trainer_id = plan_id = end = None
    if role == "member":
        tid = to_int(f.get("trainer_id"), None, 1, 10**9)
        if tid and db.execute("SELECT 1 FROM users WHERE id=? AND role='trainer'", (tid,)).fetchone():
            trainer_id = tid
        pid = to_int(f.get("plan_id"), None, 1, 10**9)
        if pid and db.execute("SELECT 1 FROM plans WHERE id=?", (pid,)).fetchone():
            plan_id = pid
        end = (date.today() + timedelta(days=30 * to_int(f.get("months"), 1, 1, 36))).isoformat()
    try:
        db.execute("INSERT INTO users (username,password_hash,name,role,trainer_id,plan_id,membership_end) "
                   "VALUES (?,?,?,?,?,?,?)",
                   (username, generate_password_hash(f["password"]), name, role, trainer_id, plan_id, end))
        db.commit()
    except IntegrityErrors:
        db.rollback()
        flash("Username sudah dipakai atau data tidak valid.", "error")
    else:
        flash(f"Akun {username} ditambahkan.", "ok")
    return back()


@bp.post("/users/<int:uid>/delete")
@login_required("admin")
def delete_user(uid):
    db = get_db()
    db.execute("DELETE FROM users WHERE id=? AND role!='admin'", (uid,))
    db.commit()
    flash("Akun dihapus.", "ok")
    return back()


@bp.post("/users/<int:uid>/extend")
@login_required("admin")
def extend(uid):
    db = get_db()
    row = db.execute("SELECT membership_end FROM users WHERE id=? AND role='member'", (uid,)).fetchone()
    if row:
        start = max(date.today(), date.fromisoformat(row["membership_end"] or date.today().isoformat()))
        new_end = (start + timedelta(days=30 * to_int(request.form.get("months"), 1, 1, 36))).isoformat()
        db.execute("UPDATE users SET membership_end=? WHERE id=?", (new_end, uid))
        db.commit()
        flash(f"Keanggotaan diperpanjang sampai {new_end}.", "ok")
    return back()


@bp.get("/equipment")
@login_required("admin")
def equipment():
    items = get_db().execute("SELECT * FROM equipment ORDER BY name").fetchall()
    return render_template("equipment.html", items=items)


@bp.post("/equipment")
@login_required("admin")
def add_equipment():
    name, qty = request.form.get("name", "").strip(), to_int(request.form.get("quantity"), 0, 0, 1000)
    if not name or qty < 1:
        flash("Isi nama alat dan jumlah minimal 1.", "error")
    else:
        db = get_db()
        db.execute("INSERT INTO equipment (name,quantity) VALUES (?,?) "
                   "ON CONFLICT(name) DO UPDATE SET quantity = equipment.quantity + excluded.quantity", (name, qty))
        db.commit()
        flash(f"{name} +{qty} disimpan.", "ok")
    return back("admin.equipment")


@bp.post("/equipment/<int:eid>/adjust")
@login_required("admin")
def adjust_equipment(eid):
    db = get_db()
    delta = to_int(request.form.get("delta"), 0, -1000, 1000)
    db.execute("UPDATE equipment SET quantity = CASE WHEN quantity + ? < 0 THEN 0 ELSE quantity + ? END WHERE id=?",
               (delta, delta, eid))
    db.commit()
    return back("admin.equipment")


@bp.post("/equipment/<int:eid>/delete")
@login_required("admin")
def delete_equipment(eid):
    db = get_db()
    db.execute("DELETE FROM equipment WHERE id=?", (eid,))
    db.commit()
    return back("admin.equipment")
