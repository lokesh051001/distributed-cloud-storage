import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.config.settings import settings
from app.models import Chunk, ChunkLocation, File
from app.services.cache_service import metadata_cache
from app.utils.crypto_utils import decrypt_bytes, encrypt_bytes

BASE_DIR = settings.storage_dir
RECONSTRUCTED = "reconstructed"
NODES_REGISTRY_PATH = os.path.join(BASE_DIR, "nodes_registry.json")
NODE_FAILURES = {}


def _ensure_nodes_registry() -> list[str]:
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(NODES_REGISTRY_PATH):
        with open(NODES_REGISTRY_PATH, "w", encoding="utf-8") as registry_file:
            json.dump({"nodes": list(settings.node_names)}, registry_file, indent=2)
    with open(NODES_REGISTRY_PATH, "r", encoding="utf-8") as registry_file:
        content = json.load(registry_file)
    nodes = content.get("nodes") or list(settings.node_names)
    return [node for node in nodes if isinstance(node, str) and node.strip()]


def _save_nodes_registry(nodes: list[str]) -> None:
    with open(NODES_REGISTRY_PATH, "w", encoding="utf-8") as registry_file:
        json.dump({"nodes": sorted(set(nodes))}, registry_file, indent=2)


def list_nodes() -> list[str]:
    return _ensure_nodes_registry()


def add_node(node_name: str) -> list[str]:
    nodes = _ensure_nodes_registry()
    if node_name not in nodes:
        nodes.append(node_name)
        _save_nodes_registry(nodes)
    os.makedirs(os.path.join(BASE_DIR, node_name), exist_ok=True)
    return _ensure_nodes_registry()


def remove_node(node_name: str) -> list[str]:
    nodes = _ensure_nodes_registry()
    nodes = [node for node in nodes if node != node_name]
    if not nodes:
        nodes = list(settings.node_names)
    _save_nodes_registry(nodes)
    return _ensure_nodes_registry()


def _node_load(node_name: str) -> int:
    node_path = os.path.join(BASE_DIR, node_name)
    if not os.path.exists(node_path):
        return 0
    return len([name for name in os.listdir(node_path) if os.path.isfile(os.path.join(node_path, name))])


def _node_used_bytes(node_name: str) -> int:
    node_path = os.path.join(BASE_DIR, node_name)
    if not os.path.exists(node_path):
        return 0
    total = 0
    for name in os.listdir(node_path):
        path = os.path.join(node_path, name)
        if os.path.isfile(path):
            total += os.path.getsize(path)
    return total


def _node_score(node_name: str) -> float:
    used_bytes = _node_used_bytes(node_name)
    file_count = _node_load(node_name)
    failure_penalty = NODE_FAILURES.get(node_name, 0)
    return (used_bytes * 0.7) + (file_count * 1024 * 0.2) + (failure_penalty * 1024 * 1024 * 0.1)


def _split_into_chunks(data: bytes, chunk_count: int) -> list[bytes]:
    if chunk_count <= 0:
        raise ValueError("chunk_count must be greater than 0")
    if not data:
        return [b""]

    base_size = max(1, len(data) // chunk_count)
    chunks = []
    for i in range(chunk_count):
        start = i * base_size
        end = None if i == chunk_count - 1 else (i + 1) * base_size
        chunk = data[start:end]
        if chunk:
            chunks.append(chunk)
    return chunks


def _choose_nodes_for_chunk() -> list[str]:
    nodes = list_nodes()
    weighted = sorted(nodes, key=_node_score)
    replication = min(settings.replication_factor, len(weighted))
    return weighted[:replication]


def _read_chunk_with_failover(chunk: Chunk) -> tuple[int, bytes]:
    for location in chunk.locations:
        chunk_path = os.path.join(BASE_DIR, location.relative_path)
        if not os.path.exists(chunk_path):
            continue
        with open(chunk_path, "rb") as chunk_file:
            encrypted_data = chunk_file.read()
        data = decrypt_bytes(encrypted_data)
        if hashlib.sha256(data).hexdigest() != chunk.chunk_hash:
            continue
        return chunk.chunk_index, data
    raise FileNotFoundError(f"All replicas missing or invalid for chunk index {chunk.chunk_index}")


def save_file_to_nodes(file_path: str, filename: str, content_type: str, db: Session) -> dict:
    with open(file_path, "rb") as file_stream:
        data = file_stream.read()

    file_record = db.query(File).filter(File.filename == filename).first()
    if file_record:
        db.delete(file_record)
        db.flush()

    file_record = File(filename=filename, content_type=content_type, size_bytes=len(data))
    db.add(file_record)
    db.flush()

    chunks = _split_into_chunks(data, settings.chunk_count)
    chunk_metadata = []

    for i, chunk in enumerate(chunks):
        chunk_hash = hashlib.sha256(chunk).hexdigest()
        chunk_record = Chunk(file_id=file_record.id, chunk_index=i, chunk_hash=chunk_hash, chunk_size=len(chunk))
        db.add(chunk_record)
        db.flush()

        selected_nodes = _choose_nodes_for_chunk()
        replica_locations = []
        for replica_index, node_name in enumerate(selected_nodes):
            node_folder = os.path.join(BASE_DIR, node_name)
            os.makedirs(node_folder, exist_ok=True)
            chunk_filename = f"{filename}.part{i}.r{replica_index}"
            relative_path = os.path.join(node_name, chunk_filename)
            chunk_path = os.path.join(BASE_DIR, relative_path)
            with open(chunk_path, "wb") as chunk_file:
                chunk_file.write(encrypt_bytes(chunk))

            location = ChunkLocation(chunk_id=chunk_record.id, node_name=node_name, relative_path=relative_path)
            db.add(location)
            replica_locations.append({"node": node_name, "path": relative_path})

        chunk_metadata.append({"index": i, "sha256": chunk_hash, "size": len(chunk), "replicas": replica_locations})

    db.commit()
    metadata_cache.delete("files:list")
    return {"id": file_record.id, "filename": file_record.filename, "size_bytes": file_record.size_bytes, "chunks": chunk_metadata}


def reconstruct_file(filename: str, db: Session) -> str:
    file_record = (
        db.query(File)
        .options(joinedload(File.chunks).joinedload(Chunk.locations))
        .filter(File.filename == filename)
        .first()
    )
    if not file_record:
        raise FileNotFoundError(f"File '{filename}' not found in metadata database.")

    output_dir = os.path.join(BASE_DIR, RECONSTRUCTED)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    ordered_chunks = sorted(file_record.chunks, key=lambda chunk: chunk.chunk_index)
    with ThreadPoolExecutor(max_workers=min(8, len(ordered_chunks) or 1)) as executor:
        recovered = list(executor.map(_read_chunk_with_failover, ordered_chunks))

    recovered.sort(key=lambda item: item[0])
    with open(output_path, "wb") as output_file:
        for _, data in recovered:
            output_file.write(data)
    return output_path


def list_uploaded_files(db: Session) -> list[dict]:
    cached = metadata_cache.get("files:list")
    if cached is not None:
        return cached
    files = db.query(File).order_by(File.created_at.desc()).all()
    result = [
        {"id": file.id, "filename": file.filename, "size": file.size_bytes, "created_at": file.created_at.isoformat()}
        for file in files
    ]
    metadata_cache.set("files:list", result, ttl_seconds=30)
    return result


def get_file_details(file_id: int, db: Session) -> dict:
    file_record = (
        db.query(File)
        .options(joinedload(File.chunks).joinedload(Chunk.locations))
        .filter(File.id == file_id)
        .first()
    )
    if not file_record:
        raise FileNotFoundError(f"File id '{file_id}' not found.")

    chunks_payload = []
    for chunk in sorted(file_record.chunks, key=lambda value: value.chunk_index):
        chunks_payload.append(
            {
                "chunk_index": chunk.chunk_index,
                "hash": chunk.chunk_hash,
                "size": chunk.chunk_size,
                "nodes": [loc.node_name for loc in chunk.locations],
            }
        )

    return {
        "file": {
            "id": file_record.id,
            "filename": file_record.filename,
            "size": file_record.size_bytes,
            "total_chunks": len(file_record.chunks),
            "created_at": file_record.created_at.isoformat(),
        },
        "chunks": chunks_payload,
    }


def delete_file(file_id: int, db: Session) -> None:
    file_record = (
        db.query(File)
        .options(joinedload(File.chunks).joinedload(Chunk.locations))
        .filter(File.id == file_id)
        .first()
    )
    if not file_record:
        raise FileNotFoundError(f"File id '{file_id}' not found.")

    for chunk in file_record.chunks:
        for location in chunk.locations:
            chunk_path = os.path.join(BASE_DIR, location.relative_path)
            if os.path.exists(chunk_path):
                os.remove(chunk_path)

    db.delete(file_record)
    db.commit()
    metadata_cache.delete("files:list")


def get_node_health_report() -> dict:
    report = {}
    for node in list_nodes():
        node_path = os.path.join(BASE_DIR, node)
        report[node] = {
            "exists": os.path.exists(node_path),
            "writable": os.access(node_path, os.W_OK) if os.path.exists(node_path) else False,
            "file_count": _node_load(node),
            "updated_at": datetime.utcnow().isoformat(),
        }
    return report


def get_node_metrics() -> dict:
    nodes = list_nodes()
    metrics = {}
    for node in nodes:
        metrics[node] = {
            "file_count": _node_load(node),
            "used_bytes": _node_used_bytes(node),
            "failure_count": NODE_FAILURES.get(node, 0),
            "score": _node_score(node),
        }
    return {"nodes": metrics}


def rebalance_storage(db: Session) -> dict:
    nodes = list_nodes()
    if len(nodes) < 2:
        return {"moved_replicas": 0, "message": "Not enough nodes to rebalance."}

    moved = 0
    files = db.query(File).options(joinedload(File.chunks).joinedload(Chunk.locations)).all()
    for file_record in files:
        for chunk in file_record.chunks:
            locations = list(chunk.locations)
            if not locations:
                continue

            metrics = get_node_metrics()["nodes"]
            source = max(locations, key=lambda loc: metrics.get(loc.node_name, {}).get("score", 0))
            target_candidates = [node for node in nodes if node not in {loc.node_name for loc in locations}]
            if not target_candidates:
                continue
            target = min(target_candidates, key=lambda node: metrics.get(node, {}).get("score", 0))

            source_path = os.path.join(BASE_DIR, source.relative_path)
            if not os.path.exists(source_path):
                NODE_FAILURES[source.node_name] = NODE_FAILURES.get(source.node_name, 0) + 1
                continue

            target_folder = os.path.join(BASE_DIR, target)
            os.makedirs(target_folder, exist_ok=True)
            target_filename = os.path.basename(source.relative_path)
            target_relative = os.path.join(target, target_filename)
            target_path = os.path.join(BASE_DIR, target_relative)

            with open(source_path, "rb") as rf:
                data = rf.read()
            with open(target_path, "wb") as wf:
                wf.write(data)

            db.add(ChunkLocation(chunk_id=chunk.id, node_name=target, relative_path=target_relative))
            db.delete(source)
            moved += 1

    db.commit()
    metadata_cache.delete("files:list")
    return {"moved_replicas": moved, "message": "Rebalance complete."}
