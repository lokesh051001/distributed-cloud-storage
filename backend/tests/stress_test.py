import concurrent.futures
import os
import random
import string
import time

import httpx

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
USERNAME = os.getenv("API_USERNAME", "admin")
PASSWORD = os.getenv("API_PASSWORD", "admin123")
REQUESTS = int(os.getenv("STRESS_REQUESTS", "30"))
WORKERS = int(os.getenv("STRESS_WORKERS", "8"))
PAYLOAD_SIZE_KB = int(os.getenv("STRESS_PAYLOAD_KB", "64"))


def login_token(client: httpx.Client) -> str:
    response = client.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD}, timeout=20)
    response.raise_for_status()
    return response.json()["access_token"]


def upload_one(index: int, token: str) -> float:
    filename = f"stress-{index}.txt"
    payload = "".join(random.choices(string.ascii_letters + string.digits, k=PAYLOAD_SIZE_KB * 1024)).encode()
    start = time.time()
    with httpx.Client(timeout=60) as client:
        response = client.post(
            f"{BASE_URL}/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, payload, "text/plain")},
        )
        response.raise_for_status()
    return time.time() - start


def main():
    with httpx.Client(timeout=20) as client:
        token = login_token(client)

    durations = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(upload_one, i, token) for i in range(REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            durations.append(future.result())

    total = sum(durations)
    avg = total / len(durations)
    print(f"Requests: {REQUESTS}")
    print(f"Workers: {WORKERS}")
    print(f"Total time: {total:.2f}s")
    print(f"Average upload time: {avg:.2f}s")


if __name__ == "__main__":
    main()
