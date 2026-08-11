// Painel de admin (login/atividade) do Shalom Reels.
(function () {
  "use strict";

  const API_BASE = window.APP_CONFIG.API_BASE_URL;
  const ADMIN_TOKEN_KEY = "reels_admin_token";
  let refreshTimer = null;

  const authSection = document.getElementById("adminAuthSection");
  const panel = document.getElementById("adminPanel");
  const logoutBox = document.getElementById("logoutBox");
  const loginForm = document.getElementById("adminLoginForm");
  const refreshBtn = document.getElementById("adminRefreshBtn");
  const logoutBtn = document.getElementById("adminLogoutBtn");
  const usersTbody = document.querySelector("#usersTable tbody");
  const loginsTbody = document.querySelector("#loginsTable tbody");

  function getToken() {
    return sessionStorage.getItem(ADMIN_TOKEN_KEY);
  }

  function setToken(token) {
    sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
  }

  function clearToken() {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  }

  function showError(message) {
    const el = document.querySelector('.form-error[data-for="adminLoginForm"]');
    if (el) el.textContent = message || "";
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("pt-BR");
  }

  async function adminFetch(path) {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (res.status === 401) {
      clearToken();
      renderAuthState();
      throw new Error("Sessão de admin expirada, entre novamente.");
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Erro (${res.status})`);
    }
    return res.json();
  }

  function renderUsers(users) {
    usersTbody.innerHTML = users
      .map(
        (u) => `
      <tr>
        <td><span class="status-pill ${u.online ? "status-completed" : "status-pending"}">${u.online ? "Online" : "Offline"}</span></td>
        <td>${u.email}</td>
        <td>${u.full_name || "—"}</td>
        <td>${fmtDate(u.created_at)}</td>
        <td>${fmtDate(u.last_seen_at)}</td>
        <td>${u.jobs_count}</td>
        <td><button type="button" class="btn btn-ghost btn-sm" data-reset-user="${u.id}" data-reset-email="${u.email}">Redefinir senha</button></td>
      </tr>`
      )
      .join("");
    if (!users.length) {
      usersTbody.innerHTML = '<tr><td colspan="7" class="empty-state">Nenhum usuário ainda.</td></tr>';
    }
  }

  async function resetUserPassword(userId, email) {
    const newPassword = prompt(`Nova senha para ${email} (mín. 8 caracteres):`);
    if (!newPassword) return;
    if (newPassword.length < 8) {
      alert("A senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}/reset-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ new_password: newPassword }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Falha ao redefinir senha");
      }
      alert(`Senha de ${email} redefinida com sucesso.`);
    } catch (err) {
      alert(err.message);
    }
  }

  usersTbody.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-reset-user]");
    if (btn) resetUserPassword(btn.dataset.resetUser, btn.dataset.resetEmail);
  });

  function renderLogins(logins) {
    loginsTbody.innerHTML = logins
      .map(
        (l) => `
      <tr>
        <td><span class="status-pill ${l.success ? "status-completed" : "status-failed"}">${l.success ? "Sucesso" : "Falhou"}</span></td>
        <td>${l.email}</td>
        <td>${l.ip_address || "—"}</td>
        <td>${fmtDate(l.created_at)}</td>
      </tr>`
      )
      .join("");
    if (!logins.length) {
      loginsTbody.innerHTML = '<tr><td colspan="4" class="empty-state">Nenhum acesso registrado ainda.</td></tr>';
    }
  }

  async function loadOverview() {
    try {
      const data = await adminFetch("/admin/overview");
      renderUsers(data.users);
      renderLogins(data.recent_logins);
    } catch (err) {
      showError(err.message);
    }
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    refreshTimer = setInterval(loadOverview, 10000);
  }

  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }

  function renderAuthState() {
    if (getToken()) {
      authSection.classList.add("hidden");
      panel.classList.remove("hidden");
      logoutBox.classList.remove("hidden");
      loadOverview();
      startAutoRefresh();
    } else {
      authSection.classList.remove("hidden");
      panel.classList.add("hidden");
      logoutBox.classList.add("hidden");
      stopAutoRefresh();
    }
  }

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError("");
    const password = new FormData(loginForm).get("password");
    try {
      const res = await fetch(`${API_BASE}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Falha no login");
      }
      const data = await res.json();
      setToken(data.access_token);
      loginForm.reset();
      renderAuthState();
    } catch (err) {
      showError(err.message);
    }
  });

  logoutBtn.addEventListener("click", () => {
    clearToken();
    renderAuthState();
  });

  refreshBtn.addEventListener("click", loadOverview);

  renderAuthState();
})();
