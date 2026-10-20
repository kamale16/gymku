import functools

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)
HOME = {"admin": "admin.index", "trainer": "trainer.index", "member": "member.index"}


@bp.before_app_request
def load_user():
    uid = session.get("user_id")
    g.user = get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None


def login_required(*roles):
    """Wajib login; kalau roles diisi, hanya peran itu yang boleh masuk."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("auth.login"))
            if roles and g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@bp.route("/")
def index():
    if g.user:
        return redirect(url_for(HOME[g.user["role"]]))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        user = get_db().execute("SELECT * FROM users WHERE username=?",
                                (request.form.get("username", "").strip(),)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], request.form.get("password", "")):
            flash("Username atau password salah.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for(HOME[user["role"]]))
    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/password", methods=("GET", "POST"))
@login_required()
def password():
    if request.method == "POST":
        old, new = request.form.get("old", ""), request.form.get("new", "")
        if not check_password_hash(g.user["password_hash"], old):
            flash("Password lama tidak cocok.", "error")
        elif len(new) < 6 or new != request.form.get("confirm", ""):
            flash("Password baru minimal 6 karakter dan harus sama dengan konfirmasinya.", "error")
        else:
            db = get_db()
            db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new), g.user["id"]))
            db.commit()
            flash("Password diganti.", "ok")
            return redirect(url_for("auth.index"))
    return render_template("password.html")
