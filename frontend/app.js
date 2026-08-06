// Frontend puro (sem build step) para o Reels Imobiliário.
(function () {
  "use strict";

  const API_BASE = window.APP_CONFIG.API_BASE_URL;
  const TOKEN_KEY = "reels_token";
  const EMAIL_KEY = "reels_email";
  const MAX_PHOTOS = 20;

  let pollTimer = null;
  let selectedFiles = [];
  let dragFromIndex = null;

  // ---------------- DOM refs ----------------
  const authSection = document.getElementById("authSection");
  const appSection = document.getElementById("appSection");
  const userBox = document.getElementById("userBox");
  const userEmailEl = document.getElementById("userEmail");
  const logoutBtn = document.getElementById("logoutBtn");

  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  const uploadForm = document.getElementById("uploadForm");

  const photosInput = document.getElementById("photosInput");
  const photoPreview = document.getElementById("photoPreview");
  const photoHint = document.getElementById("photoHint");
  const submitBtn = document.getElementById("submitBtn");
  const usageBadge = document.getElementById("usageBadge");
  const jobsList = document.getElementById("jobsList");
  const refreshBtn = document.getElementById("refreshBtn");

  // ---------------- Helpers ----------------
  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setSession(token, email) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(EMAIL_KEY, email);
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
  }

  function showError(formEl, message) {
    const el = document.querySelector(`.form-error[data-for="${formEl.id}"]`);
    if (el) el.textContent = message || "";
  }

  async function api(path, options = {}) {
    const headers = options.headers || {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.status === 401) {
      clearSession();
      renderAuthState();
      throw new Error("Sessão expirada. Faça login novamente.");
    }
    if (!res.ok) {
      let detail = `Erro (${res.status})`;
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch (_) {
        /* corpo não é JSON */
      }
      throw new Error(detail);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  // ---------------- Tabs (login/registro) ----------------
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`${btn.dataset.tab}Form`).classList.add("active");
    });
  });

  // ---------------- Auth ----------------
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(loginForm, "");
    const formData = new FormData(loginForm);
    const body = new URLSearchParams();
    body.set("username", formData.get("email"));
    body.set("password", formData.get("password"));

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Falha no login");
      }
      const data = await res.json();
      setSession(data.access_token, formData.get("email"));
      loginForm.reset();
      renderAuthState();
    } catch (err) {
      showError(loginForm, err.message);
    }
  });

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(registerForm, "");
    const formData = new FormData(registerForm);
    const payload = {
      email: formData.get("email"),
      password: formData.get("password"),
      full_name: formData.get("full_name") || null,
    };

    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Falha ao criar conta");
      }
      // Login automático após registro
      const loginBody = new URLSearchParams();
      loginBody.set("username", payload.email);
      loginBody.set("password", payload.password);
      const loginRes = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: loginBody,
      });
      const loginData = await loginRes.json();
      setSession(loginData.access_token, payload.email);
      registerForm.reset();
      renderAuthState();
    } catch (err) {
      showError(registerForm, err.message);
    }
  });

  logoutBtn.addEventListener("click", () => {
    clearSession();
    renderAuthState();
  });

  // ---------------- Upload de fotos (prévia + reordenação) ----------------
  function addFiles(fileList) {
    const incoming = Array.from(fileList || []);
    let rejected = 0;
    for (const file of incoming) {
      if (selectedFiles.length >= MAX_PHOTOS) {
        rejected += 1;
        continue;
      }
      selectedFiles.push({ file, url: URL.createObjectURL(file) });
    }
    photosInput.value = ""; // permite selecionar o mesmo arquivo de novo depois
    if (rejected > 0) {
      showError(uploadForm, `Máximo de ${MAX_PHOTOS} fotos por vídeo. ${rejected} foto(s) não adicionada(s).`);
    } else {
      showError(uploadForm, "");
    }
    renderPhotoPreview();
  }

  function removeFileAt(index) {
    const [removed] = selectedFiles.splice(index, 1);
    if (removed) URL.revokeObjectURL(removed.url);
    renderPhotoPreview();
  }

  function moveFile(index, delta) {
    const target = index + delta;
    if (target < 0 || target >= selectedFiles.length) return;
    const [item] = selectedFiles.splice(index, 1);
    selectedFiles.splice(target, 0, item);
    renderPhotoPreview();
  }

  function reorderFiles(fromIndex, toIndex) {
    if (Number.isNaN(fromIndex) || fromIndex === toIndex) return;
    const [item] = selectedFiles.splice(fromIndex, 1);
    selectedFiles.splice(toIndex, 0, item);
    renderPhotoPreview();
  }

  function clearSelectedFiles() {
    selectedFiles.forEach((item) => URL.revokeObjectURL(item.url));
    selectedFiles = [];
    renderPhotoPreview();
  }

  function renderPhotoPreview() {
    photoPreview.innerHTML = "";
    photoHint.classList.toggle("hidden", selectedFiles.length === 0);

    selectedFiles.forEach((item, index) => {
      const card = document.createElement("div");
      card.className = "photo-card";
      card.draggable = true;
      card.dataset.index = String(index);

      const img = document.createElement("img");
      img.src = item.url;
      img.alt = item.file.name;
      card.appendChild(img);

      const order = document.createElement("span");
      order.className = "photo-order";
      order.textContent = String(index + 1);
      card.appendChild(order);

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "photo-remove";
      removeBtn.textContent = "×";
      removeBtn.setAttribute("aria-label", `Remover foto ${index + 1}`);
      removeBtn.addEventListener("click", () => removeFileAt(index));
      card.appendChild(removeBtn);

      const moveRow = document.createElement("div");
      moveRow.className = "photo-move-row";

      const leftBtn = document.createElement("button");
      leftBtn.type = "button";
      leftBtn.className = "photo-move-btn";
      leftBtn.textContent = "◀";
      leftBtn.disabled = index === 0;
      leftBtn.setAttribute("aria-label", "Mover para trás");
      leftBtn.addEventListener("click", () => moveFile(index, -1));

      const rightBtn = document.createElement("button");
      rightBtn.type = "button";
      rightBtn.className = "photo-move-btn";
      rightBtn.textContent = "▶";
      rightBtn.disabled = index === selectedFiles.length - 1;
      rightBtn.setAttribute("aria-label", "Mover para frente");
      rightBtn.addEventListener("click", () => moveFile(index, 1));

      moveRow.appendChild(leftBtn);
      moveRow.appendChild(rightBtn);
      card.appendChild(moveRow);

      card.addEventListener("dragstart", () => {
        dragFromIndex = index;
        card.classList.add("dragging");
      });
      card.addEventListener("dragend", () => {
        card.classList.remove("dragging");
      });
      card.addEventListener("dragover", (e) => {
        e.preventDefault();
        card.classList.add("drag-over");
      });
      card.addEventListener("dragleave", () => {
        card.classList.remove("drag-over");
      });
      card.addEventListener("drop", (e) => {
        e.preventDefault();
        card.classList.remove("drag-over");
        reorderFiles(dragFromIndex, index);
        dragFromIndex = null;
      });

      photoPreview.appendChild(card);
    });
  }

  photosInput.addEventListener("change", () => {
    addFiles(photosInput.files);
  });

  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(uploadForm, "");

    if (selectedFiles.length === 0) {
      showError(uploadForm, "Selecione ao menos uma foto");
      return;
    }

    const formData = new FormData();
    formData.append("style", document.getElementById("styleSelect").value);
    selectedFiles.forEach((item) => formData.append("photos", item.file));

    submitBtn.disabled = true;
    submitBtn.textContent = "Enviando...";

    try {
      await api("/jobs", { method: "POST", body: formData });
      uploadForm.reset();
      clearSelectedFiles();
      await loadJobs();
      await loadUsage();
    } catch (err) {
      showError(uploadForm, err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Gerar vídeo";
    }
  });

  refreshBtn.addEventListener("click", () => {
    loadJobs();
    loadUsage();
  });

  // ---------------- Jobs ----------------
  const STATUS_LABELS = {
    pending: "Na fila",
    processing: "Processando",
    completed: "Concluído",
    failed: "Falhou",
  };

  function jobItemHtml(job) {
    const date = new Date(job.created_at).toLocaleString("pt-BR");
    const statusLabel = STATUS_LABELS[job.status] || job.status;
    let action = "";
    if (job.status === "completed") {
      action = `<button class="btn btn-primary btn-sm" data-download="${job.id}">Baixar</button>`;
    } else if (job.status === "failed") {
      action = `<span class="job-meta" title="${(job.error_message || "").replace(/"/g, "&quot;")}">Erro no processamento</span>`;
    } else {
      action = `<span class="job-meta">Aguarde...</span>`;
    }

    return `
      <div class="job-item">
        <div class="job-info">
          <span class="job-style">${job.style}</span>
          <span class="job-meta">${date} · ${job.input_photos.length} foto(s)</span>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <span class="status-pill status-${job.status}">${statusLabel}</span>
          ${action}
        </div>
      </div>`;
  }

  async function downloadJob(jobId) {
    const btn = jobsList.querySelector(`[data-download="${jobId}"]`);
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Baixando...";
    }
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/download`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error("Falha ao baixar o vídeo");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `reel-${jobId}.mp4`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Baixar";
      }
    }
  }

  jobsList.addEventListener("click", (e) => {
    const target = e.target.closest("[data-download]");
    if (target) downloadJob(target.dataset.download);
  });

  async function loadJobs() {
    try {
      const jobs = await api("/jobs");
      if (!jobs.length) {
        jobsList.innerHTML = '<p class="empty-state">Nenhum vídeo gerado ainda.</p>';
      } else {
        jobsList.innerHTML = jobs.map(jobItemHtml).join("");
      }

      const hasActiveJob = jobs.some((j) => j.status === "pending" || j.status === "processing");
      togglePolling(hasActiveJob);
    } catch (err) {
      jobsList.innerHTML = `<p class="empty-state">${err.message}</p>`;
    }
  }

  async function loadUsage() {
    try {
      const usage = await api("/usage/today");
      usageBadge.textContent = `${usage.used_today} / ${usage.limit} hoje`;
    } catch (_) {
      usageBadge.textContent = "-- / --";
    }
  }

  function togglePolling(active) {
    if (active && !pollTimer) {
      pollTimer = setInterval(loadJobs, 5000);
    } else if (!active && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  // ---------------- Render de estado ----------------
  function renderAuthState() {
    const token = getToken();
    if (token) {
      authSection.classList.add("hidden");
      appSection.classList.remove("hidden");
      userBox.classList.remove("hidden");
      userEmailEl.textContent = localStorage.getItem(EMAIL_KEY) || "";
      loadJobs();
      loadUsage();
    } else {
      authSection.classList.remove("hidden");
      appSection.classList.add("hidden");
      userBox.classList.add("hidden");
      togglePolling(false);
    }
  }

  renderAuthState();
})();
