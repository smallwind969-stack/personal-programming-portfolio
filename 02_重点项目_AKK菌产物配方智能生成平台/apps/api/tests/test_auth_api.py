from fastapi.testclient import TestClient

from app.main import app


def test_login_me_and_logout_use_server_session():
    client = TestClient(app)
    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Test-Admin-2026!"},
    )
    assert login.status_code == 200
    token = login.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "tenant_admin"
    assert me.json()["tenantId"] == "tenant-junzao-qiyuan"

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_no_public_registration_route_exists():
    response = TestClient(app).post(
        "/auth/register",
        json={"username": "public", "password": "not-allowed"},
    )
    assert response.status_code == 404
