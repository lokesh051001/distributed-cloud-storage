# Distributed Cloud File Storage System - Backend

## Overview
This backend is built with FastAPI and simulates distributed file storage by splitting files into chunks, replicating chunks across storage nodes, storing metadata in SQLAlchemy models, validating integrity with SHA-256, and reconstructing files with replica failover.

## Live Deployment
Frontend + Backend:
https://distributed-cloud-storage-production.up.railway.app
API Docs:
https://distributed-cloud-storage-production.up.railway.app/docs

## System Architecture
Client → FastAPI API → Chunk Service → Storage Nodes
                          ↓
                    Metadata Database
## Features

- JWT Authentication
- Distributed chunk storage
- Replica failover recovery
- SHA-256 integrity verification
- Weighted node balancing
- Dynamic node scaling
- Railway cloud deployment
- Interactive frontend dashboard
- Chunk metadata inspection
- Fault-tolerant download reconstruction

Flow:
1. User uploads file
2. File split into chunks
3. Chunks hashed with SHA-256
4. Replicas distributed across nodes
5. Metadata stored in database
6. Download reconstructs file from chunks
7. 
## Implemented Stack
- FastAPI
- SQLAlchemy
- Alembic
- JWT auth (`python-jose`)
- Celery scaffold
- Redis client
- Docker + Docker Compose
- Nginx reverse proxy config
- Pytest + GitHub Actions CI

## Current API
- `POST /auth/login` -> get JWT token
- `POST /upload` -> upload + split + replicate + persist metadata (auth required)
- `GET /files` -> list stored files (auth required)
- `GET /download/{filename}` -> reconstruct + stream file (auth required)
- `GET /nodes/health` -> node health snapshot (auth required)
- `GET /nodes/metrics` -> weighted balancing metrics (auth required)
- `POST /nodes/rebalance` -> move replicas from overloaded to lighter nodes (auth required)
- `GET /file/{id}/chunks` -> per-chunk mapping and hash info (auth required)
- `DELETE /file/{id}` -> delete file + chunk replicas (auth required)

## Postman POST Examples

### 1. Login
- Method: `POST`
- URL: `http://127.0.0.1:8000/auth/login`
- Headers:
  - `Content-Type: application/json`
- Body (raw, JSON):
```json
{
  "username": "admin",
  "password": "admin123"
}
```
- Expected: `200` with `access_token`

### 2. Upload File
- Method: `POST`
- URL: `http://127.0.0.1:8000/upload`
- Headers:
  - `Authorization: Bearer <access_token>`
- Body:
  - `form-data`
  - Key: `file` (type: File), Value: choose any local file
- Expected: `200`

### 3. Add Node
- Method: `POST`
- URL: `http://127.0.0.1:8000/nodes?node_name=node4`
- Headers:
  - `Authorization: Bearer <access_token>`
- Body: none
- Expected: `200` with updated node list

### 4. Rebalance Storage
- Method: `POST`
- URL: `http://127.0.0.1:8000/nodes/rebalance`
- Headers:
  - `Authorization: Bearer <access_token>`
- Body: none
- Expected: `200` with moved replica count

## Run Locally
1. `cd Cloud-Sys/backend`
2. `python -m venv venv`
3. `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and adjust values
6. `uvicorn app.main:app --reload`

Docs: `http://127.0.0.1:8000/docs`

## Frontend + Backend Connection
1. Start backend from `Cloud-Sys/backend`:
   - `uvicorn app.main:app --reload`
2. Open `Cloud-Sys/frontend/index.html` in browser.
3. Login with backend credentials (`admin` / `admin123` by default).
4. Upload, list, inspect chunk details, download, and delete files from UI.

## Test
- `python -m pytest -q`
- Stress test script:
  - `python tests/stress_test.py`

## Live Smoke Verification
Verified on May 19, 2026 using local backend on `http://127.0.0.1:8001` (used `8001` because local `8000` may be occupied by another process).

Smoke run results:
- `GET /` -> `200`
- `POST /auth/login` -> `200`
- `GET /files` (JWT) -> `200`
- `GET /nodes/health` (JWT) -> `200`
- `POST /upload` with `smoke.txt` -> `200`
- `GET /download/smoke.txt` -> `200` and payload matched (`smoke-test-payload`)

## Task Sheet Status

### Phase 1: Project Setup & Architecture
- Initialize FastAPI backend structure - Done
- Configure virtual environment and dependencies - Done
- Setup SQLAlchemy database connection - Done
- Create environment configuration (`.env`) - Done
- Design modular folder architecture - Done
- Setup logging and error handling - Done

### Phase 2: Database Design
- Create File table model - Done
- Create Chunk table model - Done
- Create ChunkLocation table model - Done
- Implement database migrations - Done
- Add indexing for faster chunk lookup - Done
- Validate metadata consistency - Done

### Phase 3: File Upload Pipeline
- Implement upload API endpoint - Done
- Validate file types and size - Done
- Implement chunk splitting logic - Done
- Generate SHA-256 hash for chunks - Done
- Store metadata in database - Done
- Handle upload exceptions gracefully - Done

### Phase 4: Distributed Storage Management
- Create storage node directories - Done
- Implement chunk distribution algorithm - Done
- Randomized node selection - Done (implemented earlier; now superseded by weighted selection for better balancing)
- Implement chunk replication - Done
- Track replica mapping - Done
- Optimize storage balancing - Done

### Phase 5: File Reconstruction & Download
- Implement chunk retrieval logic - Done
- Validate chunk integrity during retrieval - Done
- Reconstruct file in correct order - Done
- Implement download API endpoint - Done
- Handle missing/corrupt chunk recovery - Done
- Stream reconstructed file efficiently - Done

### Phase 6: Security & Fault Tolerance
- Implement authentication system - Done
- Add JWT authorization - Done
- Encrypt chunks before storage - Done
- Enable TLS/HTTPS support - Partial
- Implement node failure detection - Done
- Automatic replica failover - Done

### Phase 7: Performance & Scalability
- Parallel chunk retrieval - Done
- Asynchronous upload/download operations - Done
- Load balancing across nodes - Done (weighted by node file load)
- Caching frequently accessed metadata - Done
- Support horizontal node scaling - Done (dynamic node registry APIs)
- Stress testing with large files - Done (script provided)

### Phase 8: Testing & Deployment
- Unit testing for chunk services - Done
- Integration testing for APIs - Done
- Fault tolerance testing - Done
- Dockerize backend application - Done
- Setup CI/CD pipeline - Done
- Deploy backend server - Pending

## Production Improvements
1. Configure production `.env` values:
   - strong `JWT_SECRET_KEY`
   - strong `ENCRYPTION_KEY`
   - production `DATABASE_URL` (PostgreSQL)
2. Apply migrations in target environment:
   - `alembic upgrade head`
3. Configure TLS certificates in deployment (Nginx + HTTPS termination).
4. Deploy to your target infra (VM/Kubernetes/cloud) and wire persistent volumes + secrets.

## Task Sheet Match Check
Matched and completed in code:
- Phase 1: Completed
- Phase 2: Completed
- Phase 3: Completed
- Phase 4: Completed
- Phase 5: Completed
- Phase 6: Completed except full production TLS cert wiring
- Phase 7: Completed for current scope
- Phase 8: Completed except final production deployment execution

Still not fully complete (infrastructure execution required):
- Enable TLS/HTTPS support in deployed environment with valid certificates
- Deploy backend server to production target
