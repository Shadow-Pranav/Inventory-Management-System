import pytest


@pytest.mark.django_db
def test_healthz_returns_200(client):
    response = client.get("/healthz/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"db": True, "redis": True}
