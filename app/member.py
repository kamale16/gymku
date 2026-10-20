from datetime import date

from flask import Blueprint, g, render_template

from .auth import login_required
from .db import get_db

bp = Blueprint("member", __name__, url_prefix="/member")


@bp.get("/")
@login_required("member")
def index():
    db, uid = get_db(), g.user["id"]
    plan = db.execute("SELECT * FROM plans WHERE id=?", (g.user["plan_id"],)).fetchone()
    exercises = db.execute("SELECT * FROM plan_exercises WHERE plan_id=? ORDER BY id", (g.user["plan_id"],)).fetchall()
    trainer = db.execute("SELECT name FROM users WHERE id=?", (g.user["trainer_id"],)).fetchone()
    logs = db.execute("SELECT * FROM progress WHERE member_id=? ORDER BY log_date DESC", (uid,)).fetchall()
    counts = {r: sum(1 for x in logs if x["rating"] == r) for r in ("good", "average", "poor")}
    days_left = max((date.fromisoformat(g.user["membership_end"]) - date.today()).days, 0)
    good_pct = round(counts["good"] / len(logs) * 100) if logs else 0
    return render_template("member.html", plan=plan, exercises=exercises, trainer=trainer, logs=logs,
                           counts=counts, total=len(logs), days_left=days_left, good_pct=good_pct)
