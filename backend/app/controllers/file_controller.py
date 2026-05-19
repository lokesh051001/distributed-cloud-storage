import os
import aiofiles
from fastapi import HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.security import create_access_token
from app.services.storage_service import get_node_health_report
from app.services.storage_service import (
    add_node,
    delete_file,
    get_file_details,
    get_node_metrics,
    list_nodes,
    list_uploaded_files,
    remove_node,
    rebalance_storage,
    save_file_to_nodes,
    reconstruct_file
)
from app.schemas import LoginRequest

UPLOAD_DIR = settings.upload_dir

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _validate_upload(filename: str, file_size: int) -> None:
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    extension = os.path.splitext(filename)[1].lower()
    allow_all = "*" in settings.allowed_extensions
    if not allow_all and extension not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File extension '{extension}' is not allowed.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max upload size of {settings.max_upload_size_mb}MB.",
        )


async def upload_file(file: UploadFile = File(...), db: Session = None):
    try:
        content = await file.read()
        _validate_upload(file.filename, len(content))
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(content)

        upload_result = save_file_to_nodes(
            file_path,
            file.filename,
            file.content_type or "application/octet-stream",
            db,
        )
        return {"message": "File uploaded, split, and indexed successfully", "data": upload_result}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc


def download_file(filename: str, db: Session):
    try:
        reconstructed_path = reconstruct_file(filename, db)
        stream = open(reconstructed_path, "rb")
        return StreamingResponse(
            stream,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Download failed: {exc}") from exc


def list_files(db: Session):
    return {"files": list_uploaded_files(db)}


def login_user(payload: LoginRequest):
    if payload.username != settings.api_username or payload.password != settings.api_password:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    return {"access_token": create_access_token(payload.username), "token_type": "bearer"}


def node_health():
    return {"nodes": get_node_health_report()}


def file_details(file_id: int, db: Session):
    try:
        return get_file_details(file_id, db)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def remove_file(file_id: int, db: Session):
    try:
        delete_file(file_id, db)
        return {"message": "File deleted successfully."}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def list_nodes_controller():
    return {"nodes": list_nodes()}


def add_node_controller(node_name: str):
    return {"nodes": add_node(node_name)}


def remove_node_controller(node_name: str):
    return {"nodes": remove_node(node_name)}


def node_metrics_controller():
    return get_node_metrics()


def rebalance_controller(db: Session):
    return rebalance_storage(db)
