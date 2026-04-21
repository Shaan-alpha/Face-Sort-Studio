/**
 * Face Sort Studio — Frontend Application
 * ========================================
 * Vanilla JS (no framework needed for this scope).
 * Handles: tabs, drag-drop uploads, form submission,
 * SSE progress streaming, results display, history, dashboard.
 */

// ═══════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════
const APP_CONFIG = window.FACE_SORT_CONFIG || { publicShareMode: false };
let refFiles = [];
let galFiles = [];
let galleryMode = "upload";   // "upload" | "folder"
let matchMode = "any";        // "any" | "all"
let currentJobId = null;
let eventSource = null;

// ═══════════════════════════════════════════════════════════════
// Tabs
// ═══════════════════════════════════════════════════════════════
function showTab(name) {
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));

    const panel = document.getElementById(`panel-${name}`);
    const btn = document.getElementById(`tab-${name}`);
    if (panel) { panel.classList.remove("hidden"); panel.classList.add("animate-fadeIn"); }
    if (btn) btn.classList.add("active");

    if (name === "history") loadHistory();
    if (name === "dashboard") loadDashboard();
}

// ═══════════════════════════════════════════════════════════════
// Gallery mode toggle
// ═══════════════════════════════════════════════════════════════
function setGalleryMode(mode) {
    if (mode === "folder" && APP_CONFIG.publicShareMode) {
        galleryMode = "upload";
        return;
    }

    galleryMode = mode;
    document.querySelectorAll(".gallery-mode-btn").forEach(b => b.classList.remove("active"));
    const activeButton = document.getElementById(`gal-mode-${mode}`);
    const uploadArea = document.getElementById("gallery-upload-area");
    const folderArea = document.getElementById("gallery-folder-area");

    if (activeButton) activeButton.classList.add("active");
    if (uploadArea) uploadArea.classList.toggle("hidden", mode === "folder");
    if (folderArea) folderArea.classList.toggle("hidden", mode === "upload");
}

// ═══════════════════════════════════════════════════════════════
// Match mode toggle
// ═══════════════════════════════════════════════════════════════
function setMatchMode(mode) {
    matchMode = mode;
    document.querySelectorAll(".match-mode-btn").forEach(b => b.classList.remove("active"));
    document.getElementById(`mode-${mode}`).classList.add("active");
    document.getElementById("mode-desc").innerHTML = mode === "any"
        ? 'Match if <strong>any</strong> target person appears'
        : 'Match only if <strong>all</strong> target people appear';
}

// ═══════════════════════════════════════════════════════════════
// Threshold slider
// ═══════════════════════════════════════════════════════════════
document.getElementById("threshold").addEventListener("input", (e) => {
    document.getElementById("threshold-value").textContent = parseFloat(e.target.value).toFixed(2);
});

// ═══════════════════════════════════════════════════════════════
// File handling utilities
// ═══════════════════════════════════════════════════════════════
function addFiles(target, files) {
    const arr = target === "ref" ? refFiles : galFiles;
    for (const f of files) {
        if (f.type.startsWith("image/")) arr.push(f);
    }
    renderPreviews(target);
}

function removeFile(target, index) {
    const arr = target === "ref" ? refFiles : galFiles;
    arr.splice(index, 1);
    renderPreviews(target);
}

function renderPreviews(target) {
    const arr = target === "ref" ? refFiles : galFiles;
    const container = document.getElementById(`${target}-preview`);

    if (arr.length === 0) {
        container.classList.add("hidden");
        container.innerHTML = "";
        return;
    }

    container.classList.remove("hidden");
    container.innerHTML = arr.map((f, i) => {
        const url = URL.createObjectURL(f);
        return `
            <div class="thumb-container">
                <img src="${url}" alt="${f.name}" loading="lazy" />
                <div class="thumb-remove" onclick="removeFile('${target}', ${i})">×</div>
            </div>
        `;
    }).join("");
}

// ── Drag-and-drop + click handlers ──────────────────────────
function setupDropZone(id, inputId, target) {
    const zone = document.getElementById(id);
    const input = document.getElementById(inputId);

    ["dragenter", "dragover"].forEach(evt => {
        zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.add("dragover"); });
    });
    ["dragleave", "drop"].forEach(evt => {
        zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.remove("dragover"); });
    });
    zone.addEventListener("drop", (e) => addFiles(target, e.dataTransfer.files));
    input.addEventListener("change", (e) => addFiles(target, e.target.files));
}

setupDropZone("ref-drop", "ref-input", "ref");
setupDropZone("gal-drop", "gal-input", "gal");

// ═══════════════════════════════════════════════════════════════
// Form submission
// ═══════════════════════════════════════════════════════════════
document.getElementById("job-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    if (refFiles.length === 0) {
        showToast("Please add at least one reference photo.", "error");
        return;
    }

    if (galleryMode === "upload" && galFiles.length === 0) {
        showToast("Please add gallery photos or switch to Local Folder mode.", "error");
        return;
    }

    if (galleryMode === "folder") {
        const path = document.getElementById("gallery-path").value.trim();
        if (!path) {
            showToast("Please enter a folder path.", "error");
            return;
        }
    }

    const btn = document.getElementById("submit-btn");
    const textEl = document.getElementById("submit-text");
    const spinnerEl = document.getElementById("submit-spinner");
    btn.disabled = true;
    textEl.classList.add("hidden");
    spinnerEl.classList.remove("hidden");

    const form = new FormData();
    refFiles.forEach(f => form.append("references", f));

    if (galleryMode === "upload") {
        galFiles.forEach(f => form.append("gallery", f));
    } else {
        form.append("gallery_path", document.getElementById("gallery-path").value.trim());
    }

    form.append("match_mode", matchMode);
    form.append("threshold", document.getElementById("threshold").value);

    try {
        const res = await fetch("/api/jobs", { method: "POST", body: form });
        const data = await res.json();

        if (!res.ok) {
            showToast(data.error || "Something went wrong.", "error");
            return;
        }

        currentJobId = data.job_id;
        showProgressPanel();
        startSSE(data.job_id);

    } catch (err) {
        showToast("Network error — is the server running?", "error");
    } finally {
        btn.disabled = false;
        textEl.classList.remove("hidden");
        spinnerEl.classList.add("hidden");
    }
});

// ═══════════════════════════════════════════════════════════════
// Progress panel + SSE streaming
// ═══════════════════════════════════════════════════════════════
function showProgressPanel() {
    const panel = document.getElementById("progress-panel");
    panel.classList.remove("hidden");
    document.getElementById("progress-log").innerHTML = "";
    document.getElementById("progress-bar").style.width = "0%";
    document.getElementById("progress-status").textContent = "Processing";
    document.getElementById("progress-status").className = "px-3 py-1 text-xs font-medium rounded-full bg-apple-orange/10 text-apple-orange";
    document.getElementById("results-panel").classList.add("hidden");
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function startSSE(jobId) {
    if (eventSource) eventSource.close();

    eventSource = new EventSource(`/api/jobs/${jobId}/stream`);
    const log = document.getElementById("progress-log");
    const bar = document.getElementById("progress-bar");

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            if (data.status === "completed") {
                finishJob(jobId, true);
                eventSource.close();
                return;
            }
            if (data.status === "failed") {
                finishJob(jobId, false);
                eventSource.close();
                return;
            }

            const msg = data.msg || event.data;
            const line = document.createElement("div");
            line.className = "log-line";
            if (msg.includes("✓")) line.classList.add("success");
            if (msg.includes("✗")) line.classList.add("error");
            line.textContent = msg;
            log.appendChild(line);
            log.scrollTop = log.scrollHeight;

            // Extract percentage from messages like "[75%] ..."
            const pctMatch = msg.match(/\[(\d+)%\]/);
            if (pctMatch) bar.style.width = pctMatch[1] + "%";

        } catch { /* non-JSON line, ignore */ }
    };

    eventSource.onerror = () => {
        eventSource.close();
        // Poll once more to get final status
        setTimeout(() => pollFinalStatus(jobId), 1000);
    };
}

async function pollFinalStatus(jobId) {
    try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const data = await res.json();
        if (data.status === "completed") finishJob(jobId, true);
        else if (data.status === "failed") finishJob(jobId, false);
    } catch { /* ignore */ }
}

async function finishJob(jobId, success) {
    const statusEl = document.getElementById("progress-status");
    const bar = document.getElementById("progress-bar");

    if (success) {
        statusEl.textContent = "Completed";
        statusEl.className = "px-3 py-1 text-xs font-medium rounded-full bg-green-50 text-apple-green";
        bar.style.width = "100%";
        await showResults(jobId);
    } else {
        statusEl.textContent = "Failed";
        statusEl.className = "px-3 py-1 text-xs font-medium rounded-full bg-red-50 text-apple-red";
    }
}

// ═══════════════════════════════════════════════════════════════
// Results display
// ═══════════════════════════════════════════════════════════════
async function showResults(jobId) {
    try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = await res.json();

        const panel = document.getElementById("results-panel");
        panel.classList.remove("hidden");

        const statsEl = document.getElementById("results-stats");
        statsEl.innerHTML = `
            <div class="stat-card bg-apple-green/5">
                <div class="stat-number text-apple-green">${job.matched_count || 0}</div>
                <div class="stat-label text-apple-green">Matched</div>
            </div>
            <div class="stat-card bg-apple-orange/5">
                <div class="stat-number text-apple-orange">${job.partial_count || 0}</div>
                <div class="stat-label text-apple-orange">Partial</div>
            </div>
            <div class="stat-card bg-apple-gray-100">
                <div class="stat-number text-apple-gray-500">${job.unmatched_count || 0}</div>
                <div class="stat-label text-apple-gray-500">Unmatched</div>
            </div>
        `;

        const targetsEl = document.getElementById("results-targets");
        if (job.targets_found > 0) {
            targetsEl.innerHTML = `
                <p class="text-sm text-apple-gray-500">
                    ${job.targets_found} person(s) discovered from references &middot; 
                    Mode: <strong>${job.match_mode}</strong> &middot; 
                    Threshold: <strong>${job.threshold}</strong>
                </p>
            `;
        }

        panel.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch { /* ignore */ }
}

function openOutputFolder() {
    if (currentJobId) {
        showToast(`Output folder: data/outputs/${currentJobId}/`, "info");
    }
}

// ═══════════════════════════════════════════════════════════════
// History
// ═══════════════════════════════════════════════════════════════
async function loadHistory() {
    const container = document.getElementById("history-list");
    try {
        const res = await fetch("/api/jobs");
        const jobs = await res.json();

        if (jobs.length === 0) {
            container.innerHTML = '<p class="text-apple-gray-400 text-sm text-center py-12">No jobs yet. Start your first sort!</p>';
            return;
        }

        container.innerHTML = jobs.map(job => {
            const date = job.created_at ? new Date(job.created_at).toLocaleString() : "—";
            const badge = badgeHTML(job.status);
            return `
                <div class="history-row flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fadeIn">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            ${badge}
                            <span class="text-xs text-apple-gray-400 font-mono">${job.id.slice(0, 8)}</span>
                        </div>
                        <p class="text-xs text-apple-gray-500">${date} &middot; Mode: ${job.match_mode} &middot; Threshold: ${job.threshold}</p>
                    </div>
                    <div class="flex items-center gap-3 text-sm">
                        <span class="text-apple-green font-semibold">${job.matched_count || 0}<span class="text-xs font-normal ml-0.5 text-apple-gray-400">match</span></span>
                        <span class="text-apple-orange font-semibold">${job.partial_count || 0}<span class="text-xs font-normal ml-0.5 text-apple-gray-400">partial</span></span>
                        <span class="text-apple-gray-500 font-semibold">${job.unmatched_count || 0}<span class="text-xs font-normal ml-0.5 text-apple-gray-400">none</span></span>
                        <button onclick="deleteJob('${job.id}')" class="text-apple-red/60 hover:text-apple-red transition-colors" title="Delete">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        </button>
                    </div>
                </div>
            `;
        }).join("");
    } catch {
        container.innerHTML = '<p class="text-apple-red text-sm text-center py-12">Could not load history.</p>';
    }
}

function badgeHTML(status) {
    const map = {
        completed: '<span class="badge badge-completed">● Completed</span>',
        processing: '<span class="badge badge-processing">● Processing</span>',
        failed: '<span class="badge badge-failed">● Failed</span>',
        queued: '<span class="badge badge-queued">● Queued</span>',
    };
    return map[status] || `<span class="badge badge-queued">${status}</span>`;
}

async function deleteJob(jobId) {
    if (!confirm("Delete this job and its output files?")) return;
    try {
        await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
        loadHistory();
    } catch { /* ignore */ }
}

// ═══════════════════════════════════════════════════════════════
// Dashboard
// ═══════════════════════════════════════════════════════════════
async function loadDashboard() {
    try {
        const res = await fetch("/api/analytics");
        const data = await res.json();

        const cards = [
            { icon: "📊", label: "Total Jobs", value: data.total_jobs, color: "apple-blue" },
            { icon: "✅", label: "Completed", value: data.completed_jobs, color: "apple-green" },
            { icon: "🖼️", label: "Photos Processed", value: data.total_photos_processed, color: "apple-indigo" },
            { icon: "🎯", label: "Total Matched", value: data.total_matched, color: "apple-orange" },
        ];

        document.getElementById("dashboard-cards").innerHTML = cards.map(c => `
            <div class="dash-card animate-fadeIn">
                <div class="dash-icon bg-${c.color}/10">
                    <span class="text-xl">${c.icon}</span>
                </div>
                <div class="dash-value text-${c.color}">${c.value.toLocaleString()}</div>
                <div class="dash-label">${c.label}</div>
            </div>
        `).join("");
    } catch {
        document.getElementById("dashboard-cards").innerHTML = '<p class="text-apple-gray-400 text-sm col-span-4 text-center py-8">Could not load analytics.</p>';
    }
}

// ═══════════════════════════════════════════════════════════════
// Toast notifications
// ═══════════════════════════════════════════════════════════════
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    const bg = type === "error" ? "bg-apple-red" : type === "success" ? "bg-apple-green" : "bg-apple-gray-800";
    toast.className = `fixed bottom-6 left-1/2 -translate-x-1/2 ${bg} text-white px-5 py-3 rounded-apple text-sm font-medium shadow-apple-lg z-[9999] animate-slideUp`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ═══════════════════════════════════════════════════════════════
// Init
// ═══════════════════════════════════════════════════════════════
showTab("create");
setGalleryMode(APP_CONFIG.publicShareMode ? "upload" : galleryMode);
