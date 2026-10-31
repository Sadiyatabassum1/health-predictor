import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_service  # noqa: E402
from validators import validate_record  # noqa: E402

# (name, dob, email, glucose, haemoglobin, cholesterol, should_succeed)
CASES = [
    ("Robyn Pears", "28.01.1960", "robyn@gmail.com", "232", "13.5", "180", True),
    ("John Hunter", "10.12.1990", "hunter@gmail", "94", "15", "200", False),
    ("Darryl Tim", "12.11.1993", "timd@smh.com.au", "240", "18.6", "326", True),
    ("Peter Larry", "31.11.2001", "Larry@hotmail.com", "88", "11.5", "165", False),
    ("Sam Kerr", "09.12.2006", "sam@news.com.au", "198", "8.9", "192", True),
    ("Robyn Pears", "28.01.1960", "robyn@gmail.com", "232", "13.5", "180", False),  # duplicate
    ("Madison XI", "12.09.1998", "madison@hotmail.com", "85", "7.6", "163", True),
    ("Kris Wu", "19.10.2030", "Kris.wu.gmail.com", "79", "16.5", "197", False),
    ("Tenille Singh", "30.11.1991", "Tenille@yahoo.com", "101", "15", "310", True),
    ("Prem Kumar", "28.04.1990", "prem@telstra.com", "155", "12.5", "265", True),
]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import app as app_module
    importlib.reload(app_module)
    monkeypatch.setattr(
        ai_service, "predict_remarks", lambda *a, **k: "Mock AI remark."
    )
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def form(c):
    return dict(zip(("full_name", "dob", "email", "glucose", "haemoglobin", "cholesterol"), c[:6]))


def test_validation_flags_bad_rows():
    for c in CASES:
        _, errors = validate_record(form(c))
        if c[2] in ("hunter@gmail", "Kris.wu.gmail.com") or c[1] in ("31.11.2001", "19.10.2030"):
            assert errors, c
    _, errors = validate_record(form(CASES[0]))
    assert errors == []


def test_full_scenario(client):
    for c in CASES:
        r = client.post("/add", data=form(c))
        assert (r.status_code == 302) == c[6], (c, r.status_code)
    page = client.get("/").get_data(as_text=True)
    assert "Patient records (6)" in page
    assert "Mock AI remark." in page

    client.post("/edit/1", data={**form(CASES[0]), "email": "gokul@infocare.com"})
    assert "gokul@infocare.com" in client.get("/").get_data(as_text=True)

    client.post("/delete/2")
    assert "Patient records (5)" in client.get("/").get_data(as_text=True)


def test_ai_failure_does_not_lose_record(client, monkeypatch):
    def boom(*a, **k):
        raise ai_service.AIServiceError("no key")
    monkeypatch.setattr(ai_service, "predict_remarks", boom)
    r = client.post("/add", data=form(CASES[0]))
    assert r.status_code == 302
    assert "AI prediction unavailable" in client.get("/").get_data(as_text=True)
