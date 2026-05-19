import os

os.environ["DATABASE_URL"] = "sqlite:///./test_storage.db"

from fastapi.testclient import TestClient

from app.main import app
from app.services.storage_service import BASE_DIR


def _token(client: TestClient) -> str:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    return response.json()["access_token"]


def test_download_with_one_corrupt_replica_still_succeeds():
    with TestClient(app) as client:
        token = _token(client)
        headers = {"Authorization": f"Bearer {token}"}

        filename = "fault-test.txt"
        payload = b"replication failover check payload"
        upload = client.post("/upload", headers=headers, files={"file": (filename, payload, "text/plain")})
        assert upload.status_code == 200
        chunk_path = upload.json()["data"]["chunks"][0]["replicas"][0]["path"]

        with open(f"{BASE_DIR}/{chunk_path}".replace("\\", "/"), "wb") as chunk_file:
            chunk_file.write(b"corrupted-data")

        downloaded = client.get(f"/download/{filename}", headers=headers)
        assert downloaded.status_code == 200
        assert downloaded.content == payload
