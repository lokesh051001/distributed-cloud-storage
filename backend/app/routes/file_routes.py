from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.controllers.file_controller import (
    add_node_controller,
    file_details,
    login_user,
    list_nodes_controller,
    node_metrics_controller,
    node_health,
    download_file,
    list_files,
    remove_file,
    remove_node_controller,
    rebalance_controller,
    upload_file,
)
from app.db import get_db
from app.schemas import LoginRequest, TokenResponse
from app.security import get_current_user

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    return login_user(payload)


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return await upload_file(file, db)


@router.get("/download/{filename}")
def download(
    filename: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return download_file(filename, db)


@router.get("/files")
def files(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return list_files(db)


@router.get("/nodes/health")
def nodes(_: str = Depends(get_current_user)):
    return node_health()


@router.get("/file/{file_id}/chunks")
def chunks(file_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return file_details(file_id, db)


@router.delete("/file/{file_id}")
def file_delete(file_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return remove_file(file_id, db)


@router.get("/nodes")
def nodes_list(_: str = Depends(get_current_user)):
    return list_nodes_controller()


@router.post("/nodes")
def nodes_add(node_name: str = Query(...), _: str = Depends(get_current_user)):
    return add_node_controller(node_name)


@router.delete("/nodes")
def nodes_delete(node_name: str = Query(...), _: str = Depends(get_current_user)):
    return remove_node_controller(node_name)


@router.get("/nodes/metrics")
def nodes_metrics(_: str = Depends(get_current_user)):
    return node_metrics_controller()


@router.post("/nodes/rebalance")
def nodes_rebalance(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return rebalance_controller(db)
