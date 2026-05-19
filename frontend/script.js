const API_BASE_URL = "http://127.0.0.1:8000";
let accessToken = localStorage.getItem("access_token") || "";

function authHeaders(extra = {}) {
    return accessToken ? { ...extra, Authorization: `Bearer ${accessToken}` } : extra;
}

async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE_URL}/`);
        const online = res.ok;
        document.getElementById("api-status").classList.toggle("online", online);
        document.querySelector(".status-text").textContent = online ? "Connected" : "Offline";
        return online;
    } catch {
        document.getElementById("api-status").classList.remove("online");
        document.querySelector(".status-text").textContent = "Offline";
        return false;
    }
}

async function login() {
    try {
        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value.trim();
        const res = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        if (!res.ok) {
            let message = "Login failed";
            try {
                const error = await res.json();
                message = error.detail || message;
            } catch (_) {}
            showToast(message, "error");
            return;
        }
        const data = await res.json();
        accessToken = data.access_token;
        localStorage.setItem("access_token", accessToken);
        showToast("Logged in successfully", "success");
        loadFiles();
    } catch (err) {
        showToast("Cannot reach backend. Start API on 127.0.0.1:8000", "error");
    }
}

function logout() {
    accessToken = "";
    localStorage.removeItem("access_token");
    document.getElementById("fileList").innerHTML = `<p class="error-msg">Login to view files.</p>`;
    showToast("Logged out", "info");
}

async function uploadFile() {
    if (!accessToken) return showToast("Login first", "error");

    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];
    if (!file) return;

    const progressContainer = document.getElementById("upload-progress-container");
    const progressFill = document.getElementById("progress-fill");
    const filenameDisplay = document.getElementById("upload-filename");
    const percentageDisplay = document.getElementById("upload-percentage");

    progressContainer.classList.remove("hidden");
    filenameDisplay.textContent = file.name;
    progressFill.style.width = "0%";
    percentageDisplay.textContent = "0%";

    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            progressFill.style.width = `${percent}%`;
            percentageDisplay.textContent = `${percent}%`;
        }
    });
    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            showToast(`Uploaded ${file.name}`, "success");
            loadFiles();
        } else {
            showToast(`Upload failed (${xhr.status})`, "error");
        }
        fileInput.value = "";
        setTimeout(() => progressContainer.classList.add("hidden"), 1000);
    };
    xhr.onerror = () => {
        showToast("Upload error", "error");
        progressContainer.classList.add("hidden");
    };
    xhr.open("POST", `${API_BASE_URL}/upload`);
    if (accessToken) xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);
    xhr.send(formData);
}

async function loadFiles() {
    const container = document.getElementById("fileList");
    if (!accessToken) {
        container.innerHTML = `<p class="error-msg">Login to view files.</p>`;
        return;
    }
    const res = await fetch(`${API_BASE_URL}/files`, { headers: authHeaders() });
    if (!res.ok) {
        container.innerHTML = `<p class="error-msg">Unable to load files.</p>`;
        return;
    }
    const payload = await res.json();
    const files = payload.files || [];
    if (!files.length) {
        container.innerHTML = `<div class="empty-state glass"><i class="fas fa-folder-open"></i><p>No files uploaded yet.</p></div>`;
        return;
    }

    container.innerHTML = "";
    files.forEach((f) => {
        const card = document.createElement("div");
        card.className = "file-card glass";
        card.innerHTML = `
            <div class="file-info-main">
                <div class="file-icon"><i class="fas ${getFileIcon(f.filename)}"></i></div>
                <div class="file-name-container">
                    <span class="file-name">${f.filename}</span>
                    <div class="file-meta">
                        <span>${formatBytes(f.size || 0)}</span>
                        <span>${f.created_at ? new Date(f.created_at).toLocaleString() : ""}</span>
                    </div>
                </div>
            </div>
            <div class="file-actions">
                <button class="btn btn-ghost btn-sm" onclick="viewDetails(${f.id})"><i class="fas fa-info-circle"></i> Info</button>
                <button class="btn btn-primary btn-sm" onclick="downloadFile('${f.filename.replace(/'/g, "\\'")}')"><i class="fas fa-download"></i> Download</button>
                <button class="btn btn-ghost btn-sm delete-btn" onclick="deleteFile(${f.id})"><i class="fas fa-trash"></i></button>
            </div>
        `;
        container.appendChild(card);
    });
}

async function downloadFile(filename) {
    if (!accessToken) return showToast("Login first", "error");
    const res = await fetch(`${API_BASE_URL}/download/${encodeURIComponent(filename)}`, { headers: authHeaders() });
    if (!res.ok) return showToast("Download failed", "error");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

async function viewDetails(id) {
    const res = await fetch(`${API_BASE_URL}/file/${id}/chunks`, { headers: authHeaders() });
    if (!res.ok) return showToast("Failed to load details", "error");
    const data = await res.json();
    document.getElementById("modal-filename").textContent = data.file.filename;
    document.getElementById("modal-chunks").textContent = data.file.total_chunks;
    document.getElementById("modal-size").textContent = formatBytes(data.file.size);
    const chunkList = document.getElementById("chunk-list");
    chunkList.innerHTML = "";
    data.chunks.forEach((chunk) => {
        const item = document.createElement("div");
        item.className = "chunk-item";
        item.innerHTML = `
            <div class="chunk-info">
                <span class="chunk-label">Chunk #${chunk.chunk_index}</span>
                <span class="chunk-meta">Hash: ${chunk.hash.slice(0, 16)}...</span>
            </div>
            <div class="chunk-nodes">
                ${chunk.nodes.map((node) => `<span class="node-tag">${node}</span>`).join("")}
            </div>`;
        chunkList.appendChild(item);
    });
    document.getElementById("detailsModal").classList.remove("hidden");
}

async function deleteFile(id) {
    const res = await fetch(`${API_BASE_URL}/file/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
    });
    if (!res.ok) return showToast("Delete failed", "error");
    showToast("File deleted", "success");
    loadFiles();
}

function closeModal() {
    document.getElementById("detailsModal").classList.add("hidden");
}

function formatBytes(bytes, decimals = 2) {
    if (!bytes) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

function getFileIcon(filename) {
    const ext = filename.split(".").pop().toLowerCase();
    const map = { pdf: "fa-file-pdf", png: "fa-file-image", jpg: "fa-file-image", jpeg: "fa-file-image", txt: "fa-file-alt", py: "fa-file-code", js: "fa-file-code", zip: "fa-file-archive" };
    return map[ext] || "fa-file";
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-message">${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

const dropZone = document.getElementById("drop-zone");
dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("dragging"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragging");
    if (e.dataTransfer.files.length) {
        document.getElementById("fileInput").files = e.dataTransfer.files;
        uploadFile();
    }
});

document.getElementById("fileInput").addEventListener("change", uploadFile);
window.onclick = function (event) {
    const modal = document.getElementById("detailsModal");
    if (event.target === modal) closeModal();
};

checkHealth();
if (accessToken) loadFiles();
setInterval(checkHealth, 10000);
