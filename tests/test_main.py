from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_and_redoc():
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200

    redoc_resp = client.get("/redoc")
    assert redoc_resp.status_code == 200
