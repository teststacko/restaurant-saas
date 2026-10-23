from pathlib import Path

content = r"""let CURRENT_USER = null;
const $ = s => document.querySelector(s);
const inr = n => "₹" + Math.round(n || 0).toLocaleString("en-IN");
const today = () => new Date().toISOString().slice(0, 10);
let SCHEMA = {}, charts = [], range = 30;
const DATA_CACHE = {};

const ICONS = {
  sales: "💳",
  purchases: "🛒",
  expenses: "💸",
  wastage: "🗑️",
  inventory: "📦",
  staff: "👥",
  feedback: "⭐",
  closings: "🔒",
  dashboard: "📊",
  reports: "🧾",
  settings: "⚙️"
};

function initTheme() {
  const saved = localStorage.getItem("theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", saved);
  return saved;
}

function toggleTheme() {
  const cur = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", cur);
  localStorage.setItem("theme", cur);
  updateHeaderControls();
  if (CURRENT_USER && (!location.hash || location.hash.slice(1) === "dashboard")) {
    route();
  }
}

async function api(url, options = {}) {
  const headers = {};
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(url, { ...options, headers: { ...headers, ...(options.headers || {}) } });
  if (res.status === 401 && !url.includes("/api/auth/")) {
    CURRENT_USER = null;
    renderAuthGate();
    throw new Error("Session expired. Please log in.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "An error occurred");
  return data;
}

function toast(msg) {
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = msg;
  t.style.display = "block";
  setTimeout(() => t.style.display = "none", 2500);
}

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function init() {
  initTheme();
  try {
    const me = await api("/api/auth/me");
    if (me && me.authenticated) {
      CURRENT_USER = me.user;
    }
  } catch (e) {
    CURRENT_USER = null;
  }

  if (!CURRENT_USER) {
    renderAuthGate();
    return;
  }

  await loadApp();
}

function renderAuthGate() {
  const side = document.getElementById("side");
  const burger = document.getElementById("burger");
  if (side) side.style.display = "none";
  if (burger) burger.style.display = "none";
  
  document.getElementById("title").textContent = "";
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  document.getElementById("actions").innerHTML = '<button class="btn-icon" id="theme-btn" title="Toggle Theme">' + (isDark ? "☀️" : "🌙") + '</button>';
  document.getElementById("theme-btn").onclick = toggleTheme;

  document.getElementById("view").innerHTML = '<div style="display:flex;justify-content:center;align-items:center;min-height:75vh">' +
    '<div class="card" style="max-width:380px;width:100%;padding:28px;box-shadow:0 10px 25px -5px rgba(0,0,0,0.1)">' +
      '<div style="text-align:center;margin-bottom:20px">' +
        '<div style="font-size:38px;margin-bottom:8px">🍛</div>' +
        '<h2 style="margin:0 0 6px">Restaurant Ops</h2>' +
        '<p class="mu" style="margin:0;font-size:13px">Sign in to access your dashboard</p>' +
      '</div>' +
      '<form id="login-gate-form">' +
        '<label style="display:block;font-size:13px;color:var(--mu);margin-bottom:4px">Username</label>' +
        '<input id="g_username" value="owner" required autocomplete="username" style="width:100%;margin-bottom:12px">' +
        '<label style="display:block;font-size:13px;color:var(--mu);margin-bottom:4px">Password</label>' +
        '<input id="g_password" type="password" value="password123" required autocomplete="current-password" style="width:100%;margin-bottom:20px">' +
        '<button type="submit" class="p" style="width:100%;padding:11px">Sign In</button>' +
      '</form>' +
    '</div>' +
  '</div>';

  document.getElementById("login-gate-form").onsubmit = async e => {
    e.preventDefault();
    try {
      const res = await api("/api/auth/login", {
        method: "POST",
        body: { username: document.getElementById("g_username").value, password: document.getElementById("g_password").value }
      });
      CURRENT_USER = res.user;
      toast("Signed in as " + CURRENT_USER.username);
      await loadApp();
    } catch (err) {
      toast(err.message);
    }
  };
}

async function loadApp() {
  const side = document.getElementById("side");
  const burger = document.getElementById("burger");
  if (side) side.style.display = "flex";
  if (burger) burger.style.display = "block";
  
  SCHEMA = await api("/api/schema");
  buildSidebar();
  
  burger.onclick = () => { document.getElementById("side").classList.add("open"); document.getElementById("shade").classList.add("on"); };
  document.getElementById("shade").onclick = closeMenu;
  window.onhashchange = route;
  route();
}

function buildSidebar() {
  const items = [
    ["dashboard", ICONS.dashboard, "Dashboard"],
    ...Object.entries(SCHEMA).map(([k, s]) => [k, ICONS[k] || "📄", s.title]),
    ["reports", ICONS.reports, "Reports"],
    ["settings", ICONS.settings, "Settings & Access"]
  ];
  document.getElementById("nav").innerHTML = items.map(([k, i, t]) => '<a data-p="' + k + '"><span style="font-size:17px">' + i + '</span>' + t + '</a>').join("");
  document.getElementById("nav").onclick = e => {
    const a = e.target.closest("a");
    if (a) { location.hash = a.dataset.p; closeMenu(); }
  };
}

function closeMenu() {
  document.getElementById("side").classList.remove("open");
  document.getElementById("shade").classList.remove("on");
}

function updateHeaderControls() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const themeBtn = '<button class="btn-icon" id="theme-btn" title="Toggle Theme">' + (isDark ? "☀️" : "🌙") + '</button>';
  const userBadge = CURRENT_USER ? (
    '<div class="user-badge">' +
      '<span>👤 <strong>' + esc(CURRENT_USER.username) + '</strong></span>' +
      '<span class="badge-role">' + esc(CURRENT_USER.role) + '</span>' +
    '</div>' +
    '<button class="s" id="logout-btn">Sign Out</button>'
  ) : "";

  const actions = document.getElementById("actions");
  const custom = actions.querySelector(".view-actions") ? actions.querySelector(".view-actions").innerHTML : "";
  actions.innerHTML = '<div class="view-actions" style="display:flex;gap:8px;align-items:center">' + custom + '</div>' + themeBtn + userBadge;

  document.getElementById("theme-btn").onclick = toggleTheme;
  const lBtn = document.getElementById("logout-btn");
  if (lBtn) lBtn.onclick = logout;
}

function route() {
  if (!CURRENT_USER) { renderAuthGate(); return; }
  const p = location.hash.slice(1) || "dashboard";
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", a.dataset.p === p));
  charts.forEach(c => c.destroy());
  charts = [];
  document.getElementById("actions").innerHTML = '<div class="view-actions"></div>';
  updateHeaderControls();

  if (p === "dashboard") dashboard();
  else if (p === "reports") reports();
  else if (p === "settings") settings();
  else list(p);
}

async function logout() {
  try { await api("/api/auth/logout", { method: "POST" }); } catch (e) {}
  CURRENT_USER = null;
  location.hash = "";
  renderAuthGate();
  toast("Signed out successfully");
}

async function settings() {
  document.getElementById("title").textContent = "Settings & Team Access";
  const v = document.getElementById("view");
  v.innerHTML = '<div class="card"><p>Loading team accounts...</p></div>';

  try {
    const users = await api("/api/users");
    v.innerHTML = '<div class="grid">' +
      '<div class="card">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">' +
          '<h3 style="margin:0">Active Team Logins</h3>' +
          '<button class="p s" id="add-user-btn">+ Add Team Member</button>' +
        '</div>' +
        '<div class="wrap">' +
          '<table>' +
            '<thead><tr><th>Username</th><th>Role</th><th>Created</th></tr></thead>' +
            '<tbody>' +
              users.map(u => '<tr><td><strong>' + esc(u.username) + '</strong></td><td><span class="badge-role">' + esc(u.role) + '</span></td><td class="mu">' + (u.created_at ? u.created_at.slice(0, 10) : "System") + '</td></tr>').join("") +
            '</tbody>' +
          '</table>' +
        '</div>' +
      '</div>' +
      '<div class="card">' +
        '<h3>Theme & Display</h3>' +
        '<p class="mu">Quick theme selector:</p>' +
        '<div style="display:flex;gap:10px;margin-top:14px">' +
          '<button class="s" onclick="document.documentElement.setAttribute(\x27data-theme\x27,\x27light\x27);localStorage.setItem(\x27theme\x27,\x27light\x27);updateHeaderControls();">☀️ Light</button>' +
          '<button class="s" onclick="document.documentElement.setAttribute(\x27data-theme\x27,\x27dark\x27);localStorage.setItem(\x27theme\x27,\x27dark\x27);updateHeaderControls();">🌙 Dark</button>' +
          '<button class="s" onclick="localStorage.removeItem(\x27theme\x27);initTheme();updateHeaderControls();">💻 System Default</button>' +
        '</div>' +
      '</div>' +
    '</div>';

    document.getElementById("add-user-btn").onclick = () => {
      const m = document.getElementById("modal"), f = document.getElementById("form");
      f.innerHTML = '<h3 style="margin:0 0 12px">Create Staff Access</h3>' +
        '<label>Username</label><input id="nu_name" placeholder="e.g. cashier2" required>' +
        '<label>Password</label><input id="nu_pass" type="password" placeholder="Password" required>' +
        '<label>Role</label>' +
        '<select id="nu_role">' +
          '<option value="manager">Manager</option>' +
          '<option value="cashier" selected>Cashier</option>' +
          '<option value="chef">Chef</option>' +
        '</select>' +
        '<div class="row" style="margin-top:20px">' +
          '<button type="button" onclick="document.getElementById(\x27modal\x27).classList.remove(\x27on\x27)">Cancel</button>' +
          '<button type="submit" class="p">Create User</button>' +
        '</div>';
      m.classList.add("on");
      f.onsubmit = async e => {
        e.preventDefault();
        try {
          await api("/api/users", {
            method: "POST",
            body: { username: document.getElementById("nu_name").value, password: document.getElementById("nu_pass").value, role: document.getElementById("nu_role").value }
          });
          m.classList.remove("on");
          toast("User created!");
          settings();
        } catch (err) {
          toast(err.message);
        }
      };
    };
  } catch (err) {
    v.innerHTML = '<div class="warn">⚠️ ' + esc(err.message) + '</div>';
  }
}

const PAL = ["#c2410c", "#0f766e", "#b45309", "#4f46e5", "#be185d", "#65a30d", "#0369a1"];
function chart(id, type, labels, sets, opts = {}) {
  const el = document.getElementById(id);
  if (!el || typeof Chart === "undefined") return;
  const css = getComputedStyle(document.body);
  Chart.defaults.color = css.getPropertyValue("--mu");
  Chart.defaults.borderColor = css.getPropertyValue("--bd");
  charts.push(new Chart(el, { type, data: { labels, datasets: sets }, options: { responsive: true, maintainAspectRatio: false, ...opts } }));
}

async function dashboard() {
  document.getElementById("title").textContent = "Dashboard";
  const actions = document.getElementById("actions").querySelector(".view-actions");
  actions.innerHTML = '<select id="rg">' +
    [[7, "Last 7 days"], [30, "Last 30 days"], [90, "Last 90 days"]].map(([v, l]) => '<option value="' + v + '" ' + (v == range ? "selected" : "") + '>' + l + '</option>').join("") +
  '</select>' +
  '<button onclick="print()">Print</button>';
  
  updateHeaderControls();
  document.getElementById("rg").onchange = e => { range = +e.target.value; dashboard(); };

  const end = today(), start = new Date(Date.now() - (range - 1) * 864e5).toISOString().slice(0, 10);
  const d = await api("/api/dashboard?start=" + start + "&end=" + end), k = d.kpi;
  const card = (l, v, s = "", c = "") => '<div class="card kpi"><div class="l">' + l + '</div><div class="v ' + c + '">' + v + '</div><div class="s">' + s + '</div></div>';

  document.getElementById("view").innerHTML = (d.warnings || []).map(w => '<div class="warn">⚠️ ' + w + '</div>').join("") +
    '<div class="kpis">' +
      card("Net sales", inr(k.sales), k.orders + " orders") +
      card("Avg order value", inr(k.aov)) +
      card("Purchases", inr(k.purchases), "Owed: " + inr(k.owed)) +
      card("Expenses", inr(k.expenses)) +
      card("Est. profit", inr(k.profit), "Cash-basis estimate", k.profit < 0 ? "bad" : "ok") +
      card("Wastage cost", inr(k.wastage)) +
      card("Avg rating", k.rating ? k.rating.toFixed(1) + " ★" : "–") +
    '</div>' +
    '<div class="grid">' +
      '<div class="card"><h3>Daily Sales vs Spend</h3><div class="chart"><canvas id="c1"></canvas></div></div>' +
      '<div class="card"><h3>Payment Methods</h3><div class="chart"><canvas id="c2"></canvas></div></div>' +
    '</div>' +
    '<div class="grid">' +
      '<div class="card"><h3>Top 5 Dishes</h3><div class="chart"><canvas id="c3"></canvas></div></div>' +
      '<div class="card"><h3>Sales by Day of Week</h3><div class="chart"><canvas id="c4"></canvas></div></div>' +
    '</div>';

  const days = d.by_day.map(x => x.day), sp = Object.fromEntries(d.spend_day.map(x => [x.day, x.spend]));
  chart("c1", "bar", days, [
    { label: "Sales", data: d.by_day.map(x => x.sales), backgroundColor: "#c2410c" },
    { label: "Spending", data: days.map(x => sp[x] || 0), backgroundColor: "#0f766e" }
  ]);
  chart("c2", "doughnut", d.payments.map(x => x.k), [{ data: d.payments.map(x => x.v), backgroundColor: PAL }]);
  chart("c3", "bar", d.top_items.map(x => x.item), [{ label: "Revenue", data: d.top_items.map(x => x.revenue), backgroundColor: PAL }], { indexAxis: "y" });
  const wkd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const wkMap = Object.fromEntries(d.weekday.map(x => [x.k, x.v]));
  chart("c4", "bar", wkd, [{ label: "Sales", data: [0, 1, 2, 3, 4, 5, 6].map(i => wkMap[i] || 0), backgroundColor: "#b45309" }]);
}

async function list(t) {
  const s = SCHEMA[t];
  if (!s) return;
  document.getElementById("title").textContent = s.title;
  const actions = document.getElementById("actions").querySelector(".view-actions");
  actions.innerHTML = '<button class="p s" id="add-btn">+ Add entry</button>' +
    '<a href="/api/report/' + t + '" download><button class="s">Export CSV</button></a>';
  updateHeaderControls();
  document.getElementById("add-btn").onclick = () => form(t);

  let rows = DATA_CACHE[t];
  if (!rows) {
    document.getElementById("view").innerHTML = '<div class="card"><p class="mu">Loading ' + esc(s.title) + '...</p></div>';
    rows = await api("/api/data/" + t);
    DATA_CACHE[t] = rows;
  }

  const v = document.getElementById("view");
  v.innerHTML = '<div class="card">' +
    '<div class="tools"><input id="q" placeholder="Search ' + esc(s.title.toLowerCase()) + '..."></div>' +
    '<div class="wrap">' +
      '<table id="tbl">' +
        '<thead><tr>' + s.f.map(f => '<th>' + esc(f.l) + '</th>').join("") + '<th>Actions</th></tr></thead>' +
        '<tbody>' + renderRows(t, rows) + '</tbody>' +
      '</table>' +
    '</div>' +
  '</div>';

  document.getElementById("q").oninput = e => {
    const q = e.target.value.toLowerCase();
    const filtered = rows.filter(r => Object.values(r).some(val => String(val || "").toLowerCase().includes(q)));
    document.getElementById("tbl").querySelector("tbody").innerHTML = renderRows(t, filtered);
    bindRowActions(t);
  };
  bindRowActions(t);
}

function renderRows(t, rows) {
  if (!rows || !rows.length) return '<tr><td colspan="' + (SCHEMA[t].f.length + 1) + '" class="mu" style="text-align:center;padding:24px">No entries found</td></tr>';
  return rows.map(r => '<tr data-id="' + r.id + '">' +
    SCHEMA[t].f.map(f => '<td>' + formatCell(f, r[f.n]) + '</td>').join("") +
    '<td><button class="s edit-btn">Edit</button> <button class="s d del-btn">Delete</button></td>' +
  '</tr>').join("");
}

function formatCell(f, val) {
  if (val === null || val === undefined || val === "") return '<span class="mu">–</span>';
  if (f.n === "amount" || f.n === "paid" || f.n === "salary") return inr(val);
  return esc(val);
}

function bindRowActions(t) {
  document.querySelectorAll(".edit-btn").forEach(b => {
    b.onclick = async e => {
      const id = e.target.closest("tr").dataset.id;
      const entry = DATA_CACHE[t].find(x => String(x.id) === String(id));
      if (entry) form(t, entry);
    };
  });
  document.querySelectorAll(".del-btn").forEach(b => {
    b.onclick = async e => {
      if (!confirm("Delete this record?")) return;
      const id = e.target.closest("tr").dataset.id;
      try {
        await api("/api/data/" + t + "/" + id, { method: "DELETE" });
        DATA_CACHE[t] = DATA_CACHE[t].filter(x => String(x.id) !== String(id));
        toast("Deleted");
        list(t);
      } catch (err) {
        toast(err.message);
      }
    };
  });
}

function form(t, row = null) {
  const s = SCHEMA[t];
  const m = document.getElementById("modal"), f = document.getElementById("form");
  f.innerHTML = '<h3 style="margin:0 0 14px">' + (row ? "Edit" : "New") + ' ' + esc(s.title) + '</h3>' +
    s.f.map(field => {
      const val = row ? row[field.n] : "";
      if (field.t === "select") {
        return '<label>' + esc(field.l) + ' ' + (field.r ? "*" : "") + '</label>' +
          '<select name="' + field.n + '" ' + (field.r ? "required" : "") + '>' +
            '<option value="">Select...</option>' +
            field.o.map(opt => '<option value="' + opt + '" ' + (val === opt ? "selected" : "") + '>' + esc(opt) + '</option>').join("") +
          '</select>';
      }
      return '<label>' + esc(field.l) + ' ' + (field.r ? "*" : "") + '</label>' +
        '<input type="' + (field.t === 'number' ? 'number' : field.t === 'date' ? 'date' : 'text') + '" ' +
          'step="' + (field.t === 'number' ? 'any' : '') + '" name="' + field.n + '" value="' + esc(val ?? '') + '" ' +
          (field.r ? "required" : "") + '>';
    }).join("") +
    '<div class="row">' +
      '<button type="button" onclick="document.getElementById(\x27modal\x27).classList.remove(\x27on\x27)">Cancel</button>' +
      '<button type="submit" class="p">Save</button>' +
    '</div>';

  m.classList.add("on");
  f.onsubmit = async e => {
    e.preventDefault();
    const data = {};
    new FormData(f).forEach((v, k) => { data[k] = v === "" ? null : v; });
    try {
      if (row) {
        await api("/api/data/" + t + "/" + row.id, { method: "PUT", body: data });
        Object.assign(row, data);
        toast("Updated");
      } else {
        const res = await api("/api/data/" + t, { method: "POST", body: data });
        data.id = res.id;
        if (DATA_CACHE[t]) DATA_CACHE[t].unshift(data);
        toast("Created");
      }
      m.classList.remove("on");
      list(t);
    } catch (err) {
      toast(err.message);
    }
  };
}

function reports() {
  document.getElementById("title").textContent = "Data Reports & Export";
  document.getElementById("actions").querySelector(".view-actions").innerHTML = "";
  updateHeaderControls();
  document.getElementById("view").innerHTML = '<div class="grid">' +
    Object.entries(SCHEMA).map(([k, s]) => '<div class="card" style="display:flex;justify-content:space-between;align-items:center">' +
      '<div><h3 style="margin:0">' + (ICONS[k] || "📄") + ' ' + esc(s.title) + '</h3></div>' +
      '<a href="/api/report/' + k + '" download><button class="s">Export CSV</button></a>' +
    '</div>').join("") +
  '</div>';
}

window.onload = init;
"""

Path('../frontend/js/app.js').write_text(content, encoding='utf-8')
print("FRONTEND JS WRITTEN SUCCESSFULLY")
