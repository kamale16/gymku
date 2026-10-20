"""Akses database: SQLite untuk lokal dan tes, PostgreSQL bila DATABASE_URL diisi (mis. Neon di Vercel)."""
import os
import sqlite3
from datetime import date, timedelta

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash

try:
    import psycopg
    from psycopg.rows import dict_row
    IntegrityErrors = (sqlite3.IntegrityError, psycopg.IntegrityError)
except ImportError:  # psycopg tidak wajib kalau hanya memakai SQLite
    psycopg = None
    IntegrityErrors = (sqlite3.IntegrityError,)


class PgConn:
    """Pembungkus tipis agar kode yang sama jalan di SQLite dan PostgreSQL (placeholder ? dipakai di mana-mana)."""

    def __init__(self, url):
        self.conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10, prepare_threshold=None)

    def execute(self, sql, params=()):
        return self.conn.execute(sql.replace("?", "%s"), params)

    def executemany(self, sql, rows):
        with self.conn.cursor() as cur:
            cur.executemany(sql.replace("?", "%s"), rows)

    def executescript(self, script):
        script = script.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                self.conn.execute(statement + (" CASCADE" if statement.startswith("DROP") else ""))

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db():
    if "db" not in g:
        url = current_app.config.get("DATABASE_URL")
        if url:
            g.db = PgConn(url)
        else:
            g.db = sqlite3.connect(current_app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(seed=False):
    """Buat ulang semua tabel, lalu isi akun admin (dan data demo bila seed=True)."""
    db = get_db()
    db.executescript(current_app.open_resource("schema.sql").read().decode())
    password = os.environ.get("ADMIN_PASSWORD", "admin123")
    db.execute(
        "INSERT INTO users (username, password_hash, name, role) VALUES (?,?,?,?)",
        ("admin", generate_password_hash(password), "Administrator", "admin"),
    )
    if seed:
        seed_demo(db)
    db.commit()


def seed_demo(db):
    ph = generate_password_hash
    end = (date.today() + timedelta(days=90)).isoformat()
    db.execute("INSERT INTO users (username,password_hash,name,role) VALUES ('budi',?,'Budi Santoso','trainer')", (ph("budi1234"),))
    db.execute("INSERT INTO plans (name) VALUES ('Pemula')")
    db.executemany("INSERT INTO plan_exercises (plan_id,exercise,sets,reps) VALUES (1,?,?,?)",
                   [("Push up", 3, 10), ("Squat", 3, 12), ("Plank", 3, 30)])
    db.execute("INSERT INTO users (username,password_hash,name,role,trainer_id,plan_id,membership_end) "
               "VALUES ('siti',?,'Siti Aminah','member',2,1,?)", (ph("siti1234"), end))
    db.executemany("INSERT INTO equipment (name,quantity) VALUES (?,?)",
                   [("Dumbbell", 10), ("Barbel", 4), ("Treadmill", 3)])
    logs = [("average", "Adaptasi minggu pertama"), ("good", "Push up 3 set penuh"),
            ("good", "Squat makin stabil"), ("poor", "Kurang tidur, sesi singkat")]
    for i, (rating, note) in enumerate(logs):
        day = (date.today() - timedelta(days=(4 - i) * 2)).isoformat()
        db.execute("INSERT INTO progress (member_id,log_date,rating,note) VALUES (3,?,?,?)", (day, rating, note))


def ensure_db():
    """Buat tabel (dan data demo) hanya kalau database masih kosong."""
    db = get_db()
    try:
        db.execute("SELECT 1 FROM users LIMIT 1")
    except Exception:
        db.rollback()
        init_db(seed=current_app.config["SEED_DEMO"])


@click.command("init-db")
@click.option("--demo", is_flag=True, help="Isi dengan data demo.")
def init_db_command(demo):
    """Hapus dan buat ulang database."""
    init_db(seed=demo)
    click.echo("Database dibuat ulang.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
