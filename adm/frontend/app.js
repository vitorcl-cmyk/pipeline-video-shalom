// Shalom ADM — lógica do frontend (vanilla JS, sem build step).
const API_BASE = window.APP_CONFIG.API_BASE_URL;

const state = {
  token: localStorage.getItem("shalom_adm_token") || null,
  user: null,
  owners: [],
  tenants: [],
  properties: [],
};

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

  let payload;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${path}`, { method, headers, body: payload });

  if (res.status === 204) return null;

  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }

  if (!res.ok) {
    const detail = (data && data.detail) || res.statusText || "Erro na requisição";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

function showAuthShell() {
  document.getElementById("auth-shell").classList.remove("hidden");
  document.getElementById("app-shell").classList.add("hidden");
}

function showAppShell() {
  document.getElementById("auth-shell").classList.add("hidden");
  document.getElementById("app-shell").classList.remove("hidden");
}

async function bootstrap() {
  if (!state.token) {
    showAuthShell();
    return;
  }
  try {
    state.user = await api("/auth/me");
    document.getElementById("user-box").textContent = state.user.full_name || state.user.email;
    showAppShell();
    navigate("dashboard");
  } catch {
    logout();
  }
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("shalom_adm_token");
  showAuthShell();
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const isLogin = btn.dataset.tab === "login";
    document.getElementById("login-form").classList.toggle("hidden", !isLogin);
    document.getElementById("register-form").classList.toggle("hidden", isLogin);
  });
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("login-error");
  errEl.textContent = "";
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  try {
    const form = new URLSearchParams({ username: email, password });
    const { access_token } = await api("/auth/login", { method: "POST", form });
    state.token = access_token;
    localStorage.setItem("shalom_adm_token", access_token);
    await bootstrap();
  } catch (err) {
    errEl.textContent = err.message;
  }
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("register-error");
  errEl.textContent = "";
  const full_name = document.getElementById("reg-name").value;
  const email = document.getElementById("reg-email").value;
  const password = document.getElementById("reg-password").value;
  try {
    await api("/auth/register", { method: "POST", body: { full_name, email, password } });
    const form = new URLSearchParams({ username: email, password });
    const { access_token } = await api("/auth/login", { method: "POST", form });
    state.token = access_token;
    localStorage.setItem("shalom_adm_token", access_token);
    await bootstrap();
  } catch (err) {
    errEl.textContent = err.message;
  }
});

document.getElementById("logout-btn").addEventListener("click", logout);

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

const PAGE_LOADERS = {
  dashboard: loadDashboard,
  owners: loadOwners,
  tenants: loadTenants,
  properties: loadProperties,
  contracts: loadContracts,
};

function navigate(page) {
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === page));
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("hidden", p.id !== `page-${page}`));
  PAGE_LOADERS[page]?.();
}

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.page));
});

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

const currencyFmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const money = (v) => (v === null || v === undefined ? "—" : currencyFmt.format(v));
const dateFmt = (v) => (v ? new Date(v + "T00:00:00").toLocaleDateString("pt-BR") : "—");

const PROPERTY_STATUS_LABEL = {
  disponivel: ["Disponível", "ok"],
  alugado: ["Alugado", "warn"],
  manutencao: ["Manutenção", "muted"],
  inativo: ["Inativo", "muted"],
};

const CONTRACT_STATUS_LABEL = {
  ativo: ["Ativo", "ok"],
  encerrado: ["Encerrado", "muted"],
  inadimplente: ["Inadimplente", "danger"],
};

function badge([label, kind]) {
  return `<span class="badge ${kind}">${label}</span>`;
}

// ---------------------------------------------------------------------------
// Generic modal form
// ---------------------------------------------------------------------------

let modalSubmitHandler = null;

function openModal(title, fieldsHtml, onSubmit, populate) {
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-form").innerHTML = fieldsHtml;
  document.getElementById("modal-error").textContent = "";
  document.getElementById("modal-backdrop").classList.remove("hidden");
  if (populate) populate(document.getElementById("modal-form"));
  modalSubmitHandler = onSubmit;
}

function closeModal() {
  document.getElementById("modal-backdrop").classList.add("hidden");
  modalSubmitHandler = null;
}

document.getElementById("modal-cancel").addEventListener("click", closeModal);
document.getElementById("modal-backdrop").addEventListener("click", (e) => {
  if (e.target.id === "modal-backdrop") closeModal();
});

document.getElementById("modal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("modal-error");
  errEl.textContent = "";
  if (!modalSubmitHandler) return;
  try {
    await modalSubmitHandler(new FormData(e.target));
    closeModal();
  } catch (err) {
    errEl.textContent = err.message;
  }
});

function formValue(fd, key) {
  const v = fd.get(key);
  return v === "" ? null : v;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

async function loadDashboard() {
  const el = document.getElementById("dashboard-stats");
  el.innerHTML = "<p>Carregando...</p>";
  try {
    const s = await api("/dashboard/summary");
    el.innerHTML = [
      ["Proprietários", s.total_proprietarios],
      ["Inquilinos", s.total_inquilinos],
      ["Imóveis", s.total_imoveis],
      ["Imóveis disponíveis", s.imoveis_disponiveis],
      ["Imóveis alugados", s.imoveis_alugados],
      ["Contratos ativos", s.contratos_ativos],
      ["Vencendo em 30 dias", s.contratos_vencendo_30_dias],
      ["Receita de aluguel/mês", money(s.receita_aluguel_mensal)],
      ["Receita de administração/mês", money(s.receita_administracao_mensal)],
    ]
      .map(([label, value]) => `
        <div class="stat-card">
          <div class="label">${label}</div>
          <div class="value">${value}</div>
        </div>`)
      .join("");
  } catch (err) {
    el.innerHTML = `<p class="error-msg">${err.message}</p>`;
  }
}

// ---------------------------------------------------------------------------
// Owners
// ---------------------------------------------------------------------------

async function loadOwners() {
  const q = document.getElementById("owner-search").value.trim();
  const owners = await api(`/owners${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  state.owners = owners;
  const tbody = document.querySelector("#owners-table tbody");
  tbody.innerHTML = owners.length
    ? owners.map((o) => `
        <tr>
          <td>${o.nome}</td>
          <td>${o.cpf_cnpj || "—"}</td>
          <td>${o.telefone || "—"}</td>
          <td>${o.email || "—"}</td>
          <td class="row-actions">
            <button class="btn secondary small" data-edit="${o.id}">Editar</button>
            <button class="btn danger small" data-delete="${o.id}">Excluir</button>
          </td>
        </tr>`).join("")
    : `<tr><td colspan="5" class="empty-state">Nenhum proprietário cadastrado ainda.</td></tr>`;

  tbody.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openOwnerModal(b.dataset.edit)));
  tbody.querySelectorAll("[data-delete]").forEach((b) => b.addEventListener("click", () => deleteOwner(b.dataset.delete)));
}

function ownerFieldsHtml() {
  return `
    <label>Nome *</label><input name="nome" required />
    <div class="form-grid">
      <div><label>CPF/CNPJ</label><input name="cpf_cnpj" /></div>
      <div><label>Telefone</label><input name="telefone" /></div>
    </div>
    <label>E-mail</label><input name="email" type="email" />
    <label>Endereço</label><input name="endereco" />
    <div class="form-grid">
      <div><label>Banco</label><input name="banco" /></div>
      <div><label>Chave PIX</label><input name="chave_pix" /></div>
      <div><label>Agência</label><input name="agencia" /></div>
      <div><label>Conta</label><input name="conta" /></div>
    </div>
    <label>Observações</label><textarea name="observacoes"></textarea>
  `;
}

function openOwnerModal(id) {
  const owner = id ? state.owners.find((o) => o.id === id) : null;
  openModal(
    owner ? "Editar proprietário" : "Novo proprietário",
    ownerFieldsHtml(),
    async (fd) => {
      const payload = {
        nome: fd.get("nome"),
        cpf_cnpj: formValue(fd, "cpf_cnpj"),
        telefone: formValue(fd, "telefone"),
        email: formValue(fd, "email"),
        endereco: formValue(fd, "endereco"),
        banco: formValue(fd, "banco"),
        chave_pix: formValue(fd, "chave_pix"),
        agencia: formValue(fd, "agencia"),
        conta: formValue(fd, "conta"),
        observacoes: formValue(fd, "observacoes"),
      };
      if (owner) await api(`/owners/${owner.id}`, { method: "PUT", body: payload });
      else await api("/owners", { method: "POST", body: payload });
      await loadOwners();
    },
    (form) => {
      if (!owner) return;
      for (const [key, value] of Object.entries(owner)) {
        const input = form.elements[key];
        if (input) input.value = value ?? "";
      }
    }
  );
}

async function deleteOwner(id) {
  if (!confirm("Excluir este proprietário?")) return;
  try {
    await api(`/owners/${id}`, { method: "DELETE" });
    await loadOwners();
  } catch (err) {
    alert(err.message);
  }
}

document.getElementById("owner-new-btn").addEventListener("click", () => openOwnerModal(null));
document.getElementById("owner-search").addEventListener("input", debounce(loadOwners, 300));

// ---------------------------------------------------------------------------
// Tenants
// ---------------------------------------------------------------------------

async function loadTenants() {
  const q = document.getElementById("tenant-search").value.trim();
  const tenants = await api(`/tenants${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  state.tenants = tenants;
  const tbody = document.querySelector("#tenants-table tbody");
  tbody.innerHTML = tenants.length
    ? tenants.map((t) => `
        <tr>
          <td>${t.nome}</td>
          <td>${t.cpf_cnpj || "—"}</td>
          <td>${t.telefone || "—"}</td>
          <td>${t.email || "—"}</td>
          <td class="row-actions">
            <button class="btn secondary small" data-edit="${t.id}">Editar</button>
            <button class="btn danger small" data-delete="${t.id}">Excluir</button>
          </td>
        </tr>`).join("")
    : `<tr><td colspan="5" class="empty-state">Nenhum inquilino cadastrado ainda.</td></tr>`;

  tbody.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openTenantModal(b.dataset.edit)));
  tbody.querySelectorAll("[data-delete]").forEach((b) => b.addEventListener("click", () => deleteTenant(b.dataset.delete)));
}

function tenantFieldsHtml() {
  return `
    <label>Nome *</label><input name="nome" required />
    <div class="form-grid">
      <div><label>CPF/CNPJ</label><input name="cpf_cnpj" /></div>
      <div><label>Telefone</label><input name="telefone" /></div>
    </div>
    <label>E-mail</label><input name="email" type="email" />
    <label>Endereço</label><input name="endereco" />
    <label>Observações</label><textarea name="observacoes"></textarea>
  `;
}

function openTenantModal(id) {
  const tenant = id ? state.tenants.find((t) => t.id === id) : null;
  openModal(
    tenant ? "Editar inquilino" : "Novo inquilino",
    tenantFieldsHtml(),
    async (fd) => {
      const payload = {
        nome: fd.get("nome"),
        cpf_cnpj: formValue(fd, "cpf_cnpj"),
        telefone: formValue(fd, "telefone"),
        email: formValue(fd, "email"),
        endereco: formValue(fd, "endereco"),
        observacoes: formValue(fd, "observacoes"),
      };
      if (tenant) await api(`/tenants/${tenant.id}`, { method: "PUT", body: payload });
      else await api("/tenants", { method: "POST", body: payload });
      await loadTenants();
    },
    (form) => {
      if (!tenant) return;
      for (const [key, value] of Object.entries(tenant)) {
        const input = form.elements[key];
        if (input) input.value = value ?? "";
      }
    }
  );
}

async function deleteTenant(id) {
  if (!confirm("Excluir este inquilino?")) return;
  try {
    await api(`/tenants/${id}`, { method: "DELETE" });
    await loadTenants();
  } catch (err) {
    alert(err.message);
  }
}

document.getElementById("tenant-new-btn").addEventListener("click", () => openTenantModal(null));
document.getElementById("tenant-search").addEventListener("input", debounce(loadTenants, 300));

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

async function ensureOwnersLoaded() {
  if (!state.owners.length) state.owners = await api("/owners");
}

async function loadProperties() {
  const q = document.getElementById("property-search").value.trim();
  const [properties] = await Promise.all([
    api(`/properties${q ? `?q=${encodeURIComponent(q)}` : ""}`),
    ensureOwnersLoaded(),
  ]);
  state.properties = properties;
  const tbody = document.querySelector("#properties-table tbody");
  tbody.innerHTML = properties.length
    ? properties.map((p) => `
        <tr>
          <td>${p.endereco}${p.numero ? ", " + p.numero : ""}${p.cidade ? " — " + p.cidade : ""}</td>
          <td>${p.tipo}</td>
          <td>${p.owner ? p.owner.nome : "—"}</td>
          <td>${badge(PROPERTY_STATUS_LABEL[p.status] || [p.status, "muted"])}</td>
          <td class="row-actions">
            <button class="btn secondary small" data-edit="${p.id}">Editar</button>
            <button class="btn danger small" data-delete="${p.id}">Excluir</button>
          </td>
        </tr>`).join("")
    : `<tr><td colspan="5" class="empty-state">Nenhum imóvel cadastrado ainda.</td></tr>`;

  tbody.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openPropertyModal(b.dataset.edit)));
  tbody.querySelectorAll("[data-delete]").forEach((b) => b.addEventListener("click", () => deleteProperty(b.dataset.delete)));
}

function propertyFieldsHtml() {
  const ownerOptions = state.owners.map((o) => `<option value="${o.id}">${o.nome}</option>`).join("");
  return `
    <label>Proprietário *</label>
    <select name="owner_id" required>${ownerOptions || '<option value="">Cadastre um proprietário primeiro</option>'}</select>
    <div class="form-grid">
      <div><label>Tipo</label>
        <select name="tipo">
          <option value="apartamento">Apartamento</option>
          <option value="casa">Casa</option>
          <option value="comercial">Comercial</option>
          <option value="terreno">Terreno</option>
          <option value="outro">Outro</option>
        </select>
      </div>
      <div><label>Status</label>
        <select name="status">
          <option value="disponivel">Disponível</option>
          <option value="alugado">Alugado</option>
          <option value="manutencao">Manutenção</option>
          <option value="inativo">Inativo</option>
        </select>
      </div>
    </div>
    <label>Endereço *</label><input name="endereco" required />
    <div class="form-grid">
      <div><label>Número</label><input name="numero" /></div>
      <div><label>Complemento</label><input name="complemento" /></div>
      <div><label>Bairro</label><input name="bairro" /></div>
      <div><label>Cidade</label><input name="cidade" /></div>
      <div><label>UF</label><input name="uf" maxlength="2" /></div>
      <div><label>CEP</label><input name="cep" /></div>
    </div>
    <div class="form-grid">
      <div><label>Matrícula</label><input name="matricula" /></div>
      <div><label>IPTU anual (R$)</label><input name="valor_iptu_anual" type="number" step="0.01" /></div>
      <div><label>Condomínio (R$)</label><input name="valor_condominio" type="number" step="0.01" /></div>
    </div>
    <label>Observações</label><textarea name="observacoes"></textarea>
    <p class="hint">O status muda automaticamente para "Alugado"/"Disponível" conforme os contratos.</p>
  `;
}

function openPropertyModal(id) {
  const prop = id ? state.properties.find((p) => p.id === id) : null;
  openModal(
    prop ? "Editar imóvel" : "Novo imóvel",
    propertyFieldsHtml(),
    async (fd) => {
      const num = (key) => (fd.get(key) ? parseFloat(fd.get(key)) : null);
      const payload = {
        owner_id: fd.get("owner_id"),
        tipo: fd.get("tipo"),
        status: fd.get("status"),
        endereco: fd.get("endereco"),
        numero: formValue(fd, "numero"),
        complemento: formValue(fd, "complemento"),
        bairro: formValue(fd, "bairro"),
        cidade: formValue(fd, "cidade"),
        uf: formValue(fd, "uf"),
        cep: formValue(fd, "cep"),
        matricula: formValue(fd, "matricula"),
        valor_iptu_anual: num("valor_iptu_anual"),
        valor_condominio: num("valor_condominio"),
        observacoes: formValue(fd, "observacoes"),
      };
      if (prop) await api(`/properties/${prop.id}`, { method: "PUT", body: payload });
      else await api("/properties", { method: "POST", body: payload });
      await loadProperties();
    },
    (form) => {
      if (!prop) return;
      for (const [key, value] of Object.entries(prop)) {
        const input = form.elements[key];
        if (input) input.value = value ?? "";
      }
    }
  );
}

async function deleteProperty(id) {
  if (!confirm("Excluir este imóvel?")) return;
  try {
    await api(`/properties/${id}`, { method: "DELETE" });
    await loadProperties();
  } catch (err) {
    alert(err.message);
  }
}

document.getElementById("property-new-btn").addEventListener("click", async () => {
  await ensureOwnersLoaded();
  openPropertyModal(null);
});
document.getElementById("property-search").addEventListener("input", debounce(loadProperties, 300));

// ---------------------------------------------------------------------------
// Contracts
// ---------------------------------------------------------------------------

async function ensureTenantsLoaded() {
  if (!state.tenants.length) state.tenants = await api("/tenants");
}

async function loadContracts() {
  const [contracts] = await Promise.all([api("/contracts"), ensureOwnersLoaded(), ensureTenantsLoaded()]);
  if (!state.properties.length) state.properties = await api("/properties");
  state.contracts = contracts;
  const tbody = document.querySelector("#contracts-table tbody");
  tbody.innerHTML = contracts.length
    ? contracts.map((c) => `
        <tr>
          <td>${c.property ? c.property.endereco : "—"}</td>
          <td>${c.tenant ? c.tenant.nome : "—"}</td>
          <td>${money(c.valor_aluguel)}</td>
          <td>${dateFmt(c.data_inicio)} – ${c.data_fim ? dateFmt(c.data_fim) : "indeterminado"}</td>
          <td>${badge(CONTRACT_STATUS_LABEL[c.status] || [c.status, "muted"])}</td>
          <td class="row-actions">
            <button class="btn secondary small" data-edit="${c.id}">Editar</button>
            <button class="btn danger small" data-delete="${c.id}">Excluir</button>
          </td>
        </tr>`).join("")
    : `<tr><td colspan="6" class="empty-state">Nenhum contrato cadastrado ainda.</td></tr>`;

  tbody.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openContractModal(b.dataset.edit)));
  tbody.querySelectorAll("[data-delete]").forEach((b) => b.addEventListener("click", () => deleteContract(b.dataset.delete)));
}

function contractFieldsHtml() {
  const propertyOptions = state.properties.map((p) => `<option value="${p.id}">${p.endereco}${p.cidade ? " — " + p.cidade : ""}</option>`).join("");
  const tenantOptions = state.tenants.map((t) => `<option value="${t.id}">${t.nome}</option>`).join("");
  return `
    <div class="form-grid">
      <div><label>Imóvel *</label>
        <select name="property_id" required>${propertyOptions || '<option value="">Cadastre um imóvel primeiro</option>'}</select>
      </div>
      <div><label>Inquilino *</label>
        <select name="tenant_id" required>${tenantOptions || '<option value="">Cadastre um inquilino primeiro</option>'}</select>
      </div>
    </div>
    <div class="form-grid">
      <div><label>Início *</label><input name="data_inicio" type="date" required /></div>
      <div><label>Fim</label><input name="data_fim" type="date" /></div>
      <div><label>Dia de vencimento</label><input name="dia_vencimento" type="number" min="1" max="31" value="5" /></div>
      <div><label>Status</label>
        <select name="status">
          <option value="ativo">Ativo</option>
          <option value="encerrado">Encerrado</option>
          <option value="inadimplente">Inadimplente</option>
        </select>
      </div>
      <div><label>Valor do aluguel (R$) *</label><input name="valor_aluguel" type="number" step="0.01" required /></div>
      <div><label>Taxa de administração (%)</label><input name="taxa_administracao_percentual" type="number" step="0.01" value="10" /></div>
      <div><label>Índice de reajuste</label>
        <select name="indice_reajuste">
          <option value="igpm">IGP-M</option>
          <option value="ipca">IPCA</option>
          <option value="nenhum">Nenhum</option>
        </select>
      </div>
    </div>
    <div class="form-grid">
      <div><label>Fiador (nome)</label><input name="fiador_nome" /></div>
      <div><label>Fiador (CPF)</label><input name="fiador_cpf" /></div>
      <div><label>Fiador (telefone)</label><input name="fiador_telefone" /></div>
    </div>
    <label>Observações</label><textarea name="observacoes"></textarea>
  `;
}

function openContractModal(id) {
  const contract = id ? state.contracts.find((c) => c.id === id) : null;
  openModal(
    contract ? "Editar contrato" : "Novo contrato",
    contractFieldsHtml(),
    async (fd) => {
      const payload = {
        property_id: fd.get("property_id"),
        tenant_id: fd.get("tenant_id"),
        data_inicio: fd.get("data_inicio"),
        data_fim: formValue(fd, "data_fim"),
        dia_vencimento: parseInt(fd.get("dia_vencimento") || "5", 10),
        valor_aluguel: parseFloat(fd.get("valor_aluguel")),
        taxa_administracao_percentual: parseFloat(fd.get("taxa_administracao_percentual") || "10"),
        indice_reajuste: fd.get("indice_reajuste"),
        status: fd.get("status"),
        fiador_nome: formValue(fd, "fiador_nome"),
        fiador_cpf: formValue(fd, "fiador_cpf"),
        fiador_telefone: formValue(fd, "fiador_telefone"),
        observacoes: formValue(fd, "observacoes"),
      };
      if (contract) await api(`/contracts/${contract.id}`, { method: "PUT", body: payload });
      else await api("/contracts", { method: "POST", body: payload });
      await loadContracts();
      await loadProperties().catch(() => {});
    },
    (form) => {
      if (!contract) return;
      for (const [key, value] of Object.entries(contract)) {
        const input = form.elements[key];
        if (input && typeof value !== "object") input.value = value ?? "";
      }
      form.elements["property_id"].value = contract.property_id;
      form.elements["tenant_id"].value = contract.tenant_id;
    }
  );
}

async function deleteContract(id) {
  if (!confirm("Excluir este contrato?")) return;
  try {
    await api(`/contracts/${id}`, { method: "DELETE" });
    await loadContracts();
  } catch (err) {
    alert(err.message);
  }
}

document.getElementById("contract-new-btn").addEventListener("click", async () => {
  await Promise.all([ensureOwnersLoaded(), ensureTenantsLoaded()]);
  if (!state.properties.length) state.properties = await api("/properties");
  openContractModal(null);
});

// ---------------------------------------------------------------------------
// Utils
// ---------------------------------------------------------------------------

function debounce(fn, wait) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

bootstrap();
