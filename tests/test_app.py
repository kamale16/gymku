import os
from datetime import date, timedelta

import pytest

from app import create_app
from app.db import get_db, init_db


@pytest.fixture()
def app(tmp_path):
    """SQLite sementara; kalau TEST_DATABASE_URL diisi, tes yang sama jalan di PostgreSQL."""
    url = os.environ.get("TEST_DATABASE_URL")
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "t.sqlite"), "SEED_DEMO": True, "DATABASE_URL": url})
    with app.app_context():
        init_db(seed=True)  # mulai dari data demo yang bersih di kedua database
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def token(client):
    client.get("/login")
    with client.session_transaction() as s:
        return s["_csrf"]


def post(client, url, **data):
    return client.post(url, data={"_csrf": token(client), **data}, follow_redirects=True)


def login(client, username, password):
    return post(client, "/login", username=username, password=password)


def test_login_redirects_by_role(client):
    assert b"Akun trainer dan member" in login(client, "admin", "admin123").data
    client.post("/logout", data={"_csrf": token(client)})
    assert b"Catat progres member" in login(client, "budi", "budi1234").data
    client.post("/logout", data={"_csrf": token(client)})
    assert b"Rencana: Pemula" in login(client, "siti", "siti1234").data


def test_wrong_password_and_anonymous_redirect(client):
    assert b"Username atau password salah" in login(client, "admin", "salah").data
    assert client.get("/admin/").headers["Location"].endswith("/login")


def test_csrf_required(client):
    assert client.post("/login", data={"username": "admin", "password": "admin123"}).status_code == 400


def test_member_cannot_open_admin_or_trainer(client):
    login(client, "siti", "siti1234")
    assert client.get("/admin/").status_code == 403
    assert client.get("/trainer/").status_code == 403


def test_admin_adds_member_and_rejects_duplicate(client):
    login(client, "admin", "admin123")
    data = dict(name="Dewi", username="dewi", password="dewi1234", role="member", trainer_id="2", plan_id="1", months="2")
    assert b"Akun dewi ditambahkan" in post(client, "/admin/users", **data).data
    assert b"Username sudah dipakai" in post(client, "/admin/users", **data).data


def test_trainer_logs_progress_only_for_own_members(client, app):
    login(client, "admin", "admin123")
    post(client, "/admin/users", name="Rudi", username="rudi", password="rudi1234", role="trainer")
    post(client, "/admin/users", name="Ayu", username="ayu", password="ayu12345", role="member", trainer_id="4")
    client.post("/logout", data={"_csrf": token(client)})
    login(client, "budi", "budi1234")
    today = date.today().isoformat()
    ok = post(client, "/trainer/log", member_id="3", log_date=today, rating="good", note="Sesi bagus")
    assert b"Progres Siti Aminah" in ok.data
    other = post(client, "/trainer/log", member_id="5", log_date=today, rating="good", note="x")
    assert b"Pilih member Anda" in other.data
    future = (date.today() + timedelta(days=2)).isoformat()
    assert b"masa depan" in post(client, "/trainer/log", member_id="3", log_date=future, rating="good", note="x").data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) AS n FROM progress WHERE member_id=5").fetchone()["n"] == 0


def test_member_sees_progress(client):
    page = login(client, "siti", "siti1234").data
    assert b"Squat makin stabil" in page and b"Push up" in page


def test_equipment_stock_accumulates(client):
    login(client, "admin", "admin123")
    post(client, "/admin/equipment", name="Dumbbell", quantity="5")
    assert b"<td>15</td>" in client.get("/admin/equipment").data
    post(client, "/admin/equipment/1/adjust", delta="-100")
    assert b"<td>0</td>" in client.get("/admin/equipment").data
