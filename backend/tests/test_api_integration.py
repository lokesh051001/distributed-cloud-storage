import os

os.environ["DATABASE_URL"] = "sqlite:///./test_storage.db"

from fastapi.testclient import TestClient

from app.main import app


def _token(client: TestClient) -> str:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_upload_list_download_flow():
    with TestClient(app) as client:
        token = _token(client)
        headers = {"Authorization": f"Bearer {token}"}

        upload = client.post(
            "/upload",
            headers=headers,
            files={"file": ("integration.txt", b"hello distributed cloud storage", "text/plain")},
        )
        assert upload.status_code == 200

        listed = client.get("/files", headers=headers)
        assert listed.status_code == 200
        names = [item["filename"] for item in listed.json()["files"]]
        assert "integration.txt" in names

        downloaded = client.get("/download/integration.txt", headers=headers)
        assert downloaded.status_code == 200
        assert downloaded.content == b"hello distributed cloud storage"
