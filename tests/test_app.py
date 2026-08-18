from __future__ import annotations


def test_dashboard_and_claim_flow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TABULA_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from fastapi.testclient import TestClient

    from tabula.app import app

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Keep the record" in response.text

        created = client.post("/claims", data={"company": "Acme Holdings", "title": "Durable margin expansion", "statement": "Management expects margin expansion.", "status_value": "open", "confidence": "65", "owner": "Research", "first_seen_at": "2026-01-15"}, follow_redirects=False)
        assert created.status_code == 303
        assert "/claims/" in created.headers["location"]

        detail = client.get(created.headers["location"])
        assert detail.status_code == 200
        assert "Durable margin expansion" in detail.text
        assert "No evidence attached" in detail.text


def test_json_api_claims(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TABULA_DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    from fastapi.testclient import TestClient

    from tabula.app import app

    with TestClient(app) as client:
        payload = {"company": "Northstar", "title": "Demand remains resilient", "statement": "Demand remains resilient through the next quarter.", "status": "supported", "confidence": 80, "owner": "Strategy"}
        created = client.post("/api/claims", json=payload)
        assert created.status_code == 201
        assert created.json()["status"] == "supported"

        records = client.get("/api/claims")
        assert records.status_code == 200
        assert records.json()[0]["company"] == "Northstar"
        assert records.json()[0]["evidence_count"] == 0
