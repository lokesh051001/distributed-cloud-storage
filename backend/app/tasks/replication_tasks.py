from app.celery_app import celery_app


@celery_app.task(name="replication.verify_chunk_replication")
def verify_chunk_replication(file_id: int) -> dict:
    return {"file_id": file_id, "status": "scheduled"}
