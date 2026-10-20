import os
import secrets
from datetime import date

from flask import Flask, abort, request, session

from . import admin, auth, db, member, trainer


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(config=None):
    # File statis ada di folder public/ (cara Vercel). Flask ikut melayaninya saat dijalankan lokal.
    app = Flask(__name__, instance_relative_config=True,
                static_folder=os.path.join(ROOT, "public"), static_url_path="")
    # Di Vercel hanya /tmp yang bisa ditulisi.
    default_db = "/tmp/gymku.sqlite" if os.environ.get("VERCEL") else os.path.join(app.instance_path, "gymku.sqlite")
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-ganti-di-produksi"),
        DATABASE=os.environ.get("DATABASE", default_db),
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        SEED_DEMO=os.environ.get("SEED_DEMO", "1") == "1",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    db.init_app(app)
    for module in (auth, admin, trainer, member):
        app.register_blueprint(module.bp)

    @app.before_request
    def csrf_protect():
        session.setdefault("_csrf", secrets.token_hex(16))
        if request.method == "POST" and request.form.get("_csrf") != session["_csrf"]:
            abort(400, "Token CSRF tidak valid. Muat ulang halaman lalu coba lagi.")

    @app.context_processor
    def inject():
        return {"csrf": lambda: session.get("_csrf", ""), "today": date.today().isoformat()}

    with app.app_context():
        db.ensure_db()
    return app
