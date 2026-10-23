let CURRENT_USER = null;
const $ = s => document.querySelector(s);
let APP_CURRENCY = localStorage.getItem("app_currency") || "₹";
const inr = n => APP_CURRENCY + " " + Math.round(n || 0).toLocaleString();
let SCHEMA = {}, charts = [], range = 30;
let NAV = 0, SET_TAB = "team";
const DATA_CACHE = {}, DASH = {}, CUR = {}, LS = {}, LOGS = { page: 1, user: "", kind: "" };
const PRESETS = { cashier: ["dashboard", "sales", "closings"], manager: ["dashboard", "sales", "purchases", "expenses", "closings", "inventory", "wastage", "feedback"], chef: ["dashboard", "inventory", "wastage"] };
const ymd = d => new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
const today = () => ymd(new Date());
const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
const fmt = ts => new Date(ts).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
const closeModal = () => $("#modal").classList.remove("on");
const invalidate = t => { for (const k of Object.keys(DATA_CACHE)) if (k.startsWith(t + "|")) delete DATA_CACHE[k]; for (const k of Object.keys(DASH)) delete DASH[k]; };

//let APP_CURRENCY = localStorage.getItem("app_currency") || "₹";

function formatMoney(amount) {
  const num = Number(amount) || 0;
  return `${APP_CURRENCY}${num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

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

// Set timeout duration: 1800 for 30 minutes, 180 for 3-minute testing
const SESSION_MAX_SECONDS = 1800; 
let sessionTimer = null;
let timeLeft = SESSION_MAX_SECONDS;
let warningBannerShown = false;

function formatClock(seconds) {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function updateBadge() {
  const badge = document.getElementById("session-badge");
  if (badge) {
    badge.textContent = `⏱️ ${formatClock(timeLeft)}`;
    if (timeLeft <= 120) {
      badge.style.color = "#dc2626";
      badge.style.borderColor = "#f87171";
    } else {
      badge.style.color = "var(--mu)";
      badge.style.borderColor = "var(--bd)";
    }
  }
}

function showSessionWarningBanner() {
  if (document.getElementById("session-warning-banner")) return;
  warningBannerShown = true;

  const banner = document.createElement("div");
  banner.id = "session-warning-banner";
  banner.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 99999;
    background: #ef4444;
    color: #ffffff;
    padding: 14px 18px;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    font-size: 14px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 12px;
  `;

  banner.innerHTML = `
    <span>⚠️ Inactivity Alert: Session auto-locks in <span id="warn-sec">${timeLeft}</span>s.</span>
    <button id="btn-stay-active" style="background:#ffffff;color:#dc2626;border:none;padding:5px 12px;border-radius:5px;font-weight:bold;cursor:pointer;">Stay Signed In</button>
    <button id="btn-dismiss-warn" style="background:transparent;color:#ffffff;border:none;font-size:16px;cursor:pointer;margin-left:4px;" title="Dismiss">✖</button>
  `;

  document.body.appendChild(banner);

  const dismiss = () => {
    resetTimer();
    removeSessionWarningBanner();
  };

  document.getElementById("btn-stay-active").onclick = dismiss;
  document.getElementById("btn-dismiss-warn").onclick = dismiss;
}

function removeSessionWarningBanner() {
  const banner = document.getElementById("session-warning-banner");
  if (banner) banner.remove();
  warningBannerShown = false;
}

function resetTimer() {
  timeLeft = SESSION_MAX_SECONDS;
  updateBadge();
  if (warningBannerShown) {
    removeSessionWarningBanner();
  }
}


function initTheme() {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  return saved;
}

// Stores independent filter settings per section
const SECTION_FILTERS = {
  dashboard: {
    start: new Date(Date.now() - 29 * 864e5).toISOString().slice(0, 10),
    end: new Date().toISOString().slice(0, 10),
    activePreset: "30D"
  }
};

function getSectionFilter(sec) {
  if (!SECTION_FILTERS[sec]) {
    SECTION_FILTERS[sec] = {
      start: new Date(Date.now() - 29 * 864e5).toISOString().slice(0, 10),
      end: new Date().toISOString().slice(0, 10),
      activePreset: "30D",
      page: 1,
      q: ""
    };
  }
  return SECTION_FILTERS[sec];
}

function setPresetRange(sec, days) {
  const f = getSectionFilter(sec);
  const end = new Date().toISOString().slice(0, 10);
  const start = new Date(Date.now() - (days - 1) * 864e5).toISOString().slice(0, 10);
  f.start = start;
  f.end = end;
  f.activePreset = days === 1 ? "1D" : days === 3 ? "3D" : days === 7 ? "7D" : days === 15 ? "15D" : "30D";
  f.page = 1;
}

function renderDateRangeToolbar(sec, onApplyCallback) {
  const f = getSectionFilter(sec);
  const presets = [
    { label: "Today (1D)", days: 1, id: "1D" },
    { label: "3D", days: 3, id: "3D" },
    { label: "7D", days: 7, id: "7D" },
    { label: "15D", days: 15, id: "15D" },
    { label: "30D", days: 30, id: "30D" }
  ];

  return `
    <div class="date-filter-bar card" style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:14px;padding:10px 14px;border:1px solid var(--bd);">
      <span style="font-weight:600;font-size:13px;color:var(--fg)">📅 Range:</span>
      <div style="display:flex;align-items:center;gap:6px">
        <input type="date" id="${sec}-date-start" value="${f.start}" style="padding:4px 8px;font-size:13px;border-radius:6px;border:1px solid var(--bd)">
        <span style="color:var(--mu)">➔</span>
        <input type="date" id="${sec}-date-end" value="${f.end}" style="padding:4px 8px;font-size:13px;border-radius:6px;border:1px solid var(--bd)">
        <button class="s p" id="${sec}-date-apply" style="padding:5px 12px;font-size:12px">Apply</button>
        <button class="s" id="${sec}-date-reset" style="padding:5px 10px;font-size:12px" title="Reset to default 30 days">✖ Reset</button>
      </div>
      <div style="display:flex;align-items:center;gap:4px;margin-left:auto">
        ${presets.map(p => `
          <button class="s preset-btn ${f.activePreset === p.id ? 'p' : ''}" 
                  data-sec="${sec}" data-days="${p.days}" data-id="${p.id}"
                  style="padding:4px 9px;font-size:12px;font-weight:600">
            ${p.label}
          </button>
        `).join('')}
      </div>
    </div>
  `;
}

function bindDateRangeEvents(sec, reloadFn) {
  const f = getSectionFilter(sec);
  const applyBtn = document.getElementById(`${sec}-date-apply`);
  if (applyBtn) {
    applyBtn.onclick = () => {
      const sVal = document.getElementById(`${sec}-date-start`).value;
      const eVal = document.getElementById(`${sec}-date-end`).value;
      if (!sVal || !eVal) {
        toast("Please choose both Start and End dates");
        return;
      }
      if (sVal > eVal) {
        toast("Start date cannot be after End date");
        return;
      }
      f.start = sVal;
      f.end = eVal;
      f.activePreset = "custom";
      f.page = 1;
      reloadFn();
    };
  }

  const resetBtn = document.getElementById(`${sec}-date-reset`);
  if (resetBtn) {
    resetBtn.onclick = () => {
      setPresetRange(sec, 30);
      reloadFn();
    };
  }

  document.querySelectorAll(`.preset-btn[data-sec="${sec}"]`).forEach(btn => {
    btn.onclick = () => {
      const days = parseInt(btn.dataset.days, 10);
      setPresetRange(sec, days);
      reloadFn();
    };
  });
}
function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
  
  // Update the button icon in the header directly without reloading #view
  const btn = document.querySelector(".theme-btn") || document.getElementById("theme-btn");
  if (btn) {
    btn.textContent = next === "dark" ? "☀️" : "🌙";
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
    if (me && me.authenticated) CURRENT_USER = me.user; 
  } catch (e) { 
    CURRENT_USER = null; 
  }
  if (!CURRENT_USER) { renderAuthGate(); return; }

  // Sync saved restaurant currency
  try {
    const metaData = await api("/api/meta");
    if (metaData && metaData.currency) {
      APP_CURRENCY = metaData.currency;
      localStorage.setItem("app_currency", APP_CURRENCY);
    }
  } catch (_) {}

  initSessionTimer();
  await loadApp();
}

function renderAuthGate() {
  showShell(false); NAV++;
  for (const o of [DATA_CACHE, DASH, CUR, LS]) for (const k of Object.keys(o)) delete o[k];   // never show one user's cached data to the next
  $("#title").textContent = "";
  const dark = document.documentElement.getAttribute("data-theme") === "dark";
  $("#actions").innerHTML = '<button class="btn-icon" id="theme-btn" title="Toggle theme" aria-label="Toggle theme">' + (dark ? "☀️" : "🌙") + "</button>";
  $("#theme-btn").onclick = toggleTheme;
  setView('<div class="login-wrap"><div class="card login-card"><div style="text-align:center;margin-bottom:20px"><div style="font-size:38px">🏨</div><h2 style="margin:6px 0">Amber Fort Hotel Operation</h2><p class="mu" style="margin:0;font-size:13px">Sign in to continue</p></div>' +
    '<form id="login-gate-form"><label class="lbl" for="g_username">Username</label><input id="g_username" required autocomplete="username" autofocus style="width:100%;margin-bottom:12px">' +
    '<label class="lbl" for="g_password">Password</label>' + pwField("g_password", "current-password").replace("<input ", '<input style="margin-bottom:0" ') +
    '<div id="g_err" class="bad small" role="alert" style="min-height:20px;margin:8px 0"></div><button type="submit" id="g_btn" class="p" style="width:100%;padding:11px">Sign in</button></form></div></div>');
  $("#login-gate-form").onsubmit = async e => {
    e.preventDefault(); const btn = $("#g_btn"), err = $("#g_err"); btn.disabled = true; btn.textContent = "Signing in…"; err.textContent = "";
    try {
      const res = await api("/api/auth/login", { method: "POST", body: { username: $("#g_username").value, password: $("#g_password").value } });
      CURRENT_USER = res.user; await loadApp();
    } catch (ex) { err.textContent = ex.message; btn.disabled = false; btn.textContent = "Sign in"; }
  };
}

function initSessionTimer() {
  // Activity listeners reset the timer automatically
  ["click", "keypress", "scroll", "touchstart"].forEach(evt => {
    document.removeEventListener(evt, resetTimer);
    document.addEventListener(evt, resetTimer, { passive: true });
  });

  updateBadge();

  clearInterval(sessionTimer);
  sessionTimer = setInterval(async () => {
    timeLeft--;
    updateBadge();

    // Update countdown text inside warning banner if active
    const warnSec = document.getElementById("warn-sec");
    if (warnSec) warnSec.textContent = timeLeft;

    // Trigger persistent warning at 2 minutes (120 seconds)
    if (timeLeft <= 120 && !warningBannerShown) {
      showSessionWarningBanner();
    }

    // Auto-logout when timer hits zero
// Auto-logout when timer hits zero
    if (timeLeft <= 0) {
      clearInterval(sessionTimer);
      removeSessionWarningBanner();
      toast("🔒 Signed out due to inactivity. Please click Sign In.");

      if (typeof logout === "function") {
        await logout();
      } else {
        try {
          await api("/api/auth/logout", { method: "POST" });
        } catch (_) {}
        document.cookie = "session_id=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;";
        CURRENT_USER = null;
        if (typeof renderAuthGate === "function") {
          renderAuthGate();
        } else {
          location.reload();
        }
      }
      return;
    }
  }, 1000);
}


async function loadApp() {
  showShell(true); NAV++; setView(dskel());          // show the app shell immediately, never leave the login card on screen
  $("#burger").onclick = () => { $("#side").classList.add("open"); $("#shade").classList.add("on"); };
  $("#shade").onclick = closeMenu; window.onhashchange = route;
  try { if (!Object.keys(SCHEMA).length) SCHEMA = await api("/api/schema"); } catch (e) { toast(e.message); return; }
  buildSidebar(); updateHeaderControls();
  if (CURRENT_USER.must_set_password) passwordModal(true);
  route();
}

function buildSidebar() {
  const owner = CURRENT_USER.role === "owner" || CURRENT_USER.role === "superadmin", a = CURRENT_USER.allowed_sections || [], all = isAllAccess(), items = [];
  if (all || a.includes("dashboard")) items.push(["dashboard", ICONS.dashboard, "Dashboard"]);
  for (const [k, s] of Object.entries(SCHEMA)) if (all || a.includes(k)) items.push([k, ICONS[k] || "📄", s.title]);
  //if (all || a.includes("reports")) items.push(["reports", ICONS.reports, "Reports"]);
  if (owner) items.push(["settings", ICONS.settings, "Settings & Access"]);
  $("#nav").innerHTML = items.map(([k, i, t]) => '<a data-p="' + k + '" tabindex="0"><span style="font-size:17px">' + i + "</span>" + t + "</a>").join("");
  $("#nav").onclick = e => { const x = e.target.closest("a"); if (x) { location.hash = x.dataset.p; closeMenu(); } };
}

function closeMenu() {
  document.getElementById("side").classList.remove("open");
  document.getElementById("shade").classList.remove("on");
}

// ===============================================================================
// 30-MINUTE INACTIVITY SESSION TIMER & ACTIVITY DETECTOR
// ===============================================================================

function updateHeaderControls() {
  const dark = document.documentElement.getAttribute("data-theme") === "dark",
        acts = $("#actions"),
        custom = acts.querySelector(".view-actions") ? acts.querySelector(".view-actions").innerHTML : "";

  const timerBadgeHtml = CURRENT_USER
    ? '<span id="session-badge" style="margin-right:8px;font-size:12px;font-weight:600;color:var(--mu);padding:3px 9px;border:1px solid var(--bd);border-radius:12px;cursor:help;white-space:nowrap" title="Auto-locks after 30 mins of inactivity">⏱️ ' + formatClock(timeLeft) + '</span>'
    : '';

  acts.innerHTML = '<div class="view-actions" style="display:flex;gap:8px;align-items:center">' + custom + "</div>" +
    timerBadgeHtml +
    '<button class="btn-icon" id="theme-btn" title="Toggle theme" aria-label="Toggle theme">' + (dark ? "☀️" : "🌙") + "</button>" +
    (CURRENT_USER ? '<button class="btn-icon" id="pw-btn" title="Change password" aria-label="Change password">🔑</button><div class="user-badge"><span>👤 <strong>' + esc(CURRENT_USER.username) + '</strong></span><span class="badge-role">' + esc(CURRENT_USER.role) + '</span></div><button class="s" id="logout-btn">Sign Out</button>' : "");

  $("#theme-btn").onclick = toggleTheme;
  if ($("#pw-btn")) $("#pw-btn").onclick = () => passwordModal(false);
  if ($("#logout-btn")) $("#logout-btn").onclick = logout;
}
function route() {
  if (!CURRENT_USER) { renderAuthGate(); return; }
  const p = location.hash.slice(1) || homePage(); NAV++;
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", a.dataset.p === p));
  charts.forEach(c => c.destroy()); charts = [];
  $("#actions").innerHTML = '<div class="view-actions"></div>'; updateHeaderControls();
  if (p === "none") { $("#title").textContent = ""; setView('<div class="card"><p>No sections are enabled for your account yet. Please ask the owner.</p></div>'); }
  else if (p === "dashboard") dashboard(); else if (p === "settings") settings(); else list(p);
}

async function logout() {
  try { await api("/api/auth/logout", { method: "POST" }); } catch (e) {}
  CURRENT_USER = null;
  location.hash = "";
  renderAuthGate();
  toast("Signed out successfully");
}

async function settings() {
  const my = NAV; $("#title").textContent = "Settings & Access";
  $("#actions").querySelector(".view-actions").innerHTML = ""; updateHeaderControls(); setView(skel(6), my);
  let users, meta;
  try { [users, meta] = await Promise.all([api("/api/users"), api("/api/meta")]); } catch (e) { setView('<div class="warn">⚠️ ' + esc(e.message) + "</div>", my); return; }
  const tabs = [["team", "👥 Team & Access"], ["roles", "🏷️ Roles"], ["logs", "📜 Activity Log"], ["look", "🎨 Appearance"]];
  if (!setView('<div class="tabs">' + tabs.map(([k, l]) => '<button data-tab="' + k + '">' + l + "</button>").join("") + '</div><div id="tab"></div>', my)) return;
  const show = () => { document.querySelectorAll("[data-tab]").forEach(b => b.classList.toggle("on", b.dataset.tab === SET_TAB)); ({ team: teamTab, roles: rolesTab, logs: logsTab, look: lookTab })[SET_TAB](users, meta); };
  document.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => { SET_TAB = b.dataset.tab; show(); });
  show();
}



const PAL = ["#c2410c", "#0f766e", "#b45309", "#4f46e5", "#be185d", "#65a30d", "#0369a1"];
function chart(id, type, labels, sets, opts = {}, tries = 0) {
  const el = document.getElementById(id); if (!el) return;
  if (typeof Chart === "undefined") { if (tries < 25) setTimeout(() => chart(id, type, labels, sets, opts, tries + 1), 200); return; }
  const css = getComputedStyle(document.body); Chart.defaults.color = css.getPropertyValue("--mu"); Chart.defaults.borderColor = css.getPropertyValue("--bd");
  charts.push(new Chart(el, { type, data: { labels, datasets: sets }, options: { responsive: true, maintainAspectRatio: false, ...opts } }));
}

async function dashboard() {
  document.getElementById("title").textContent = "Dashboard";
  const f = getSectionFilter("dashboard");

  const actions = document.getElementById("actions").querySelector(".view-actions");
  if (actions) {
    actions.innerHTML = '<button class="s" onclick="window.print()">🖨️ Print</button>';
  }
  updateHeaderControls();

  const v = document.getElementById("view");
  v.innerHTML = renderDateRangeToolbar("dashboard", dashboard) +
                '<div id="dash-content"><div class="card"><p class="mu">Loading Dashboard...</p></div></div>';

  bindDateRangeEvents("dashboard", dashboard);

  try {
    const d = await api(`/api/dashboard?start=${f.start}&end=${f.end}`);
    const k = d.kpi;
    const card = (l, val, s = "", c = "", tip = "") => `
      <div class="card kpi" title="${esc(tip)}">
        <div class="l" style="display:flex;align-items:center;justify-content:space-between">
          <span>${l}</span>
          ${tip ? '<span style="font-size:11px;opacity:0.65;cursor:help">ℹ️</span>' : ''}
        </div>
        <div class="v ${c}">${val}</div>
        <div class="s">${s}</div>
      </div>
    `;

    let kpiCards = "";
    if (k.sales !== undefined) {
      kpiCards += card("Net sales", inr(k.sales), `${k.orders || 0} orders`, "", "Total completed order revenue");
    }
    if (k.aov !== undefined) {
      kpiCards += card("Avg order value", inr(k.aov), "", "", "Net Sales ÷ Total unique order count");
    }
    if (k.purchases !== undefined) {
      kpiCards += card("Purchases", inr(k.purchases), "Owed: " + inr(k.owed || 0), "", "Procurement spend on raw inventory");
    }
    if (k.expenses !== undefined) {
      kpiCards += card("Expenses", inr(k.expenses), "", "", "Overhead operating costs (gas, rent, cleaning)");
    }
    if (k.wastage !== undefined) {
      kpiCards += card("Wastage cost", inr(k.wastage), "", "", "Spoiled, damaged, or expired stock loss");
    }
    if (k.profit !== undefined) {
      kpiCards += card("Est. profit", inr(k.profit), "Net Sales - (Purchases + Expenses + Wastage)", k.profit < 0 ? "bad" : "ok", "Net Sales − (Purchases + Expenses + Wastage)");
    }
    if (k.rating !== undefined) {
      kpiCards += card("Avg rating", k.rating ? k.rating.toFixed(1) + " ★" : "–", "", "", "Customer feedback average");
    }

    let lowStockHtml = "";
    if (d.low_stock && d.low_stock.length > 0) {
      lowStockHtml = `
        <div class="card" style="border-left:4px solid #ef4444;margin-bottom:14px">
          <h3 style="margin:0 0 8px;color:#dc2626">⚠️ Low-Stock Alerts (${d.low_stock.length} Items)</h3>
          <div style="display:flex;flex-wrap:wrap;gap:8px">
            ${d.low_stock.map(item => `
              <span class="badge-role" style="background:#fee2e2;color:#991b1b;border:1px solid #f87171;padding:4px 8px">
                <strong>${esc(item.name)}</strong>: ${item.on_hand} ${item.unit} (Alert at ≤ ${item.low_at})
              </span>
            `).join("")}
          </div>
        </div>
      `;
    }

    let cashMismatchesHtml = "";
    if (d.cash_diffs && d.cash_diffs.length > 0) {
      cashMismatchesHtml = `
        <div class="card" style="border-left:4px solid #f59e0b;margin-top:16px">
          <h3 style="margin:0 0 8px;color:#b45309">⚠️ Cash Closing Mismatches (${d.cash_diffs.length} Shifts)</h3>
          <div style="display:flex;flex-direction:column;gap:6px">
            ${d.cash_diffs.map(cd => `
              <div style="font-size:13px;color:var(--fg)">
                <strong>${esc(cd.day)}</strong>: Counted <strong>${inr(cd.actual)}</strong> vs Expected <strong>${inr(cd.expected)}</strong> 
                <span class="${cd.diff < 0 ? 'bad' : 'ok'}" style="font-weight:600;margin-left:6px">(${cd.diff > 0 ? '+' : ''}${inr(cd.diff)})</span>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    const showSalesSpend = d.can_finances && d.by_day && d.by_day.length > 0;
    const showPayments = d.payments && d.payments.length > 0;

    let row1ChartsHtml = "";
    if (showSalesSpend && showPayments) {
      row1ChartsHtml = `
        <div class="grid">
          <div class="card"><h3>Daily Sales vs Spend</h3><div class="chart"><canvas id="c1"></canvas></div></div>
          <div class="card"><h3>Payment Methods</h3><div class="chart"><canvas id="c2"></canvas></div></div>
        </div>
      `;
    } else if (showSalesSpend) {
      row1ChartsHtml = `
        <div class="grid">
          <div class="card"><h3>Daily Sales vs Spend</h3><div class="chart"><canvas id="c1"></canvas></div></div>
        </div>
      `;
    } else if (showPayments) {
      row1ChartsHtml = `
        <div class="grid">
          <div class="card" style="max-width:540px"><h3>Payment Methods</h3><div class="chart"><canvas id="c2"></canvas></div></div>
        </div>
      `;
    }

    document.getElementById("dash-content").innerHTML = `
      ${lowStockHtml}
      <div class="kpis">${kpiCards}</div>
      ${row1ChartsHtml}
      <div class="grid">
        <div class="card"><h3>Top 5 Dishes</h3><div class="chart"><canvas id="c3"></canvas></div></div>
        <div class="card"><h3>Sales by Day of Week</h3><div class="chart"><canvas id="c4"></canvas></div></div>
      </div>
      ${cashMismatchesHtml}
    `;

    // Render Chart.js
    const days = (d.by_day || []).map(x => x.day);
    if (showSalesSpend && document.getElementById("c1")) {
      const sp = Object.fromEntries((d.spend_day || []).map(x => [x.day, x.spend]));
      chart("c1", "bar", days, [
        { label: "Sales", data: d.by_day.map(x => x.sales), backgroundColor: "#c2410c" },
        { label: "Spending (Purchases+Exp+Waste)", data: days.map(x => sp[x] || 0), backgroundColor: "#0f766e" }
      ]);
    }
    if (showPayments && document.getElementById("c2")) {
      // Semantic high-contrast colors: Cash, UPI, Card, Delivery
      const payColors = { cash: "#16a34a", upi: "#2563eb", card: "#9333ea", delivery: "#ea580c" };
      const colors = d.payments.map(x => payColors[x.k.toLowerCase()] || "#64748b");
      chart("c2", "doughnut", d.payments.map(x => x.k), [{ data: d.payments.map(x => x.v), backgroundColor: colors }]);
    }
    if (d.top_items && d.top_items.length > 0 && document.getElementById("c3")) {
      chart("c3", "bar", d.top_items.map(x => x.item), [{ label: "Revenue", data: d.top_items.map(x => x.revenue), backgroundColor: PAL }], { indexAxis: "y" });
    }
    if (d.weekday && d.weekday.length > 0 && document.getElementById("c4")) {
      const wkd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
      const wkMap = Object.fromEntries(d.weekday.map(x => [x.k, x.v]));
      chart("c4", "bar", wkd, [{ label: "Sales", data: [0, 1, 2, 3, 4, 5, 6].map(i => wkMap[i] || 0), backgroundColor: "#b45309" }]);
    }
  } catch (err) {
    document.getElementById("dash-content").innerHTML = `<div class="warn">⚠️ ${esc(err.message)}</div>`;
  }
}
async function list(t) {
  const s = SCHEMA[t];
  if (!s) return;
  document.getElementById("title").textContent = s.title;

  const isOwner = CURRENT_USER.role === "owner" || CURRENT_USER.role === "superadmin";
  const actions = document.getElementById("actions").querySelector(".view-actions");
  actions.innerHTML = `
    <button class="p s" id="add-btn">+ Add entry</button>
    ${isOwner ? `<a href="/api/report/${t}" download><button class="s">Export CSV</button></a>` : ""}
  `;
  updateHeaderControls();
  document.getElementById("add-btn").onclick = () => form(t);

  const hasDay = s.f.some(field => field.n === "day");
  const f = getSectionFilter(t);

  const v = document.getElementById("view");
  const toolbarHtml = hasDay ? renderDateRangeToolbar(t, () => list(t)) : "";

  v.innerHTML = `
    ${toolbarHtml}
    <div class="card">
      <div class="tools" style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px">
        <input id="q" placeholder="Search ${esc(s.title.toLowerCase())}..." value="${esc(f.q || '')}" style="max-width:320px">
        <span class="mu" id="total-count-label" style="font-size:13px">Loading entries...</span>
      </div>
      <div class="wrap">
        <table id="tbl">
          <thead>
            <tr>
              ${s.f.map(field => `<th>${esc(field.l)}</th>`).join("")}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="tbl-body">
            <tr><td colspan="${s.f.length + 1}" class="mu" style="text-align:center;padding:24px">Loading entries...</td></tr>
          </tbody>
        </table>
      </div>
      <div id="pagination-controls" style="display:flex;justify-content:space-between;align-items:center;margin-top:14px;padding-top:12px;border-top:1px solid var(--bd)"></div>
    </div>
  `;

  if (hasDay) {
    bindDateRangeEvents(t, () => list(t));
  }

  // Handle Search Input with debounce
  let searchTimer;
  document.getElementById("q").oninput = e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      f.q = e.target.value;
      f.page = 1;
      fetchTableData(t);
    }, 280);
  };

  await fetchTableData(t);
}

async function fetchTableData(t) {
  const s = SCHEMA[t];
  const hasDay = s.f.some(field => field.n === "day");
  const f = getSectionFilter(t);

  let url = `/api/data/${t}?page=${f.page}&page_size=10&q=${encodeURIComponent(f.q || "")}`;
  if (hasDay && f.start && f.end) {
    url += `&start=${f.start}&end=${f.end}`;
  }

  try {
    const res = await api(url);
    DATA_CACHE[t] = res.items;

    document.getElementById("total-count-label").textContent = `Total: ${res.total} entries (Page ${res.page} of ${res.total_pages})`;
    document.getElementById("tbl-body").innerHTML = renderRows(t, res.items);
    bindRowActions(t);

    // Build Pagination Controls
    const pag = document.getElementById("pagination-controls");
    pag.innerHTML = `
      <div style="font-size:13px;color:var(--mu)">
        Showing ${res.items.length === 0 ? 0 : (res.page - 1) * 10 + 1}–${Math.min(res.total, res.page * 10)} of ${res.total}
      </div>
      <div style="display:flex;gap:6px">
        <button class="s" id="prev-page-btn" ${res.page <= 1 ? "disabled" : ""}>◀ Prev</button>
        <span style="display:flex;align-items:center;padding:0 8px;font-weight:600;font-size:13px">${res.page} / ${res.total_pages}</span>
        <button class="s" id="next-page-btn" ${res.page >= res.total_pages ? "disabled" : ""}>Next ▶</button>
      </div>
    `;

    document.getElementById("prev-page-btn").onclick = () => {
      if (f.page > 1) {
        f.page--;
        fetchTableData(t);
      }
    };

    document.getElementById("next-page-btn").onclick = () => {
      if (f.page < res.total_pages) {
        f.page++;
        fetchTableData(t);
      }
    };
  } catch (err) {
    document.getElementById("tbl-body").innerHTML = `<tr><td colspan="${s.f.length + 1}" class="warn">${esc(err.message)}</td></tr>`;
  }
}
function renderRows(t, items) {
  const s = SCHEMA[t];
  if (!items || items.length === 0) {
    return `<tr><td colspan="${s.f.length + 1}" class="mu" style="text-align:center;padding:24px">No entries found</td></tr>`;
  }
  return items.map(row => `
    <tr>
      ${s.f.map(field => `<td>${formatCell(field, row[field.n])}</td>`).join("")}
      <td style="white-space:nowrap">
        <button class="s edit-btn" data-id="${row.id}" style="padding:2px 8px;margin-right:4px">Edit</button>
        <button class="s del-btn bad" data-id="${row.id}" style="padding:2px 8px">Delete</button>
      </td>
    </tr>
  `).join("");
}
function formatCell(f, val) {
  if (val === null || val === undefined || val === "") return '<span class="mu">–</span>';
  if (f.n === "amount" || f.n === "paid" || f.n === "salary") return inr(val);

  // Check for image type or bill field
  if (f.t === "image" || f.n === "bill" || f.n === "bill_photo") {
    const ext = String(val).split(".").pop().toLowerCase();
    const isImg = ["jpg", "jpeg", "png"].includes(ext);
    return `<a href="${esc(val)}" target="_blank" class="s" style="padding:2px 8px;font-size:12px;text-decoration:none">${isImg ? "🖼️ View Image" : "📄 View File"}</a>`;
  }

  return esc(val);
}

function bindRowActions(t) {
  const tblBody = document.getElementById("tbl-body");
  if (!tblBody) return;

  // Clone node to strip any old listeners cleanly
  const newBody = tblBody.cloneNode(true);
  tblBody.parentNode.replaceChild(newBody, tblBody);

  newBody.addEventListener("click", async (e) => {
    const editBtn = e.target.closest(".edit-btn");
    if (editBtn) {
      const rowId = editBtn.dataset.id;
      const row = (DATA_CACHE[t] || []).find(r => String(r.id) === String(rowId));
      form(t, row);
      return;
    }

    const delBtn = e.target.closest(".del-btn");
    if (delBtn) {
      if (confirm("Are you sure you want to delete this entry?")) {
        try {
          await api(`/api/data/${t}/${delBtn.dataset.id}`, { method: "DELETE" });
          toast("🗑️ Entry deleted successfully");
          if (typeof invalidate === "function") invalidate(t);
          fetchTableData(t);
        } catch (err) {
          toast("⚠️ " + err.message);
        }
      }
    }
  });
}

function form(t, row = null) {
  const s = SCHEMA[t];
  const m = document.getElementById("modal"), f = document.getElementById("form");

  f.innerHTML = '<h3 style="margin:0 0 14px">' + (row ? "Edit" : "New") + ' ' + esc(s.title) + '</h3>' +
    s.f.map(field => {
      const val = row ? row[field.n] : "";

      // 1. File Upload Field for Bill photo (handles f.t === "image" or f.n === "bill")
   // 1. File Upload Field for Bill photo (handles f.t === "image" or f.n === "bill")
      if (field.t === "image" || field.n === "bill" || field.n === "bill_photo") {
        return '<label>' + esc(field.l) + ' ' + (field.r ? "*" : "") + '</label>' +
          '<input type="file" id="fi_' + field.n + '" accept=".jpg,.jpeg,.png,.pdf,.txt,.csv" style="margin-bottom:6px">' +
          '<input type="hidden" id="f_' + field.n + '" name="' + field.n + '" value="' + esc(val ?? '') + '">' +
          '<div id="preview_' + field.n + '" style="margin-bottom:12px;font-size:13px">' +
            (val ? '<a href="' + esc(val) + '" target="_blank" style="color:var(--ac);text-decoration:underline">📄 View Current File</a>' : '<span class="mu">No file attached</span>') +
          '</div>';
      }

      // 2. Select Fields
      if (field.t === "select") {
        return '<label>' + esc(field.l) + ' ' + (field.r ? "*" : "") + '</label>' +
          '<select name="' + field.n + '" id="f_' + field.n + '" ' + (field.r ? "required" : "") + '>' +
            '<option value="">Select...</option>' +
            field.o.map(opt => '<option value="' + opt + '" ' + (val === opt ? "selected" : "") + '>' + esc(opt) + '</option>').join("") +
          '</select>';
      }

      // 3. Number, Date, and Text Fields
      return '<label>' + esc(field.l) + ' ' + (field.r ? "*" : "") + '</label>' +
        '<input type="' + (field.t === 'number' ? 'number' : field.t === 'date' ? 'date' : 'text') + '" ' +
          'step="' + (field.t === 'number' ? 'any' : '') + '" id="f_' + field.n + '" name="' + field.n + '" value="' + esc(val ?? '') + '" ' +
          (field.r ? "required" : "") + '>';
    }).join("") +
    '<div class="row">' +
      '<button type="button" onclick="document.getElementById(\x27modal\x27).classList.remove(\x27on\x27)">Cancel</button>' +
      '<button type="submit" class="p">Save</button>' +
    '</div>';

  m.classList.add("on");

  // Auto-calculate Expected Cash when picking date in Cash Closings
  if (t === "closings") {
    setTimeout(() => {
      const dateInput = document.getElementById("f_day");
      const expInput = document.getElementById("f_expected");
      if (dateInput && expInput) {
        dateInput.onchange = async (e) => {
          const dVal = e.target.value;
          if (!dVal) return;
          try {
            const res = await api(`/api/data/sales?start=${dVal}&end=${dVal}&page_size=500`);
            const cashTotal = (res.items || [])
              .filter(x => x.method === 'cash')
              .reduce((sum, x) => sum + Number(x.amount || 0), 0);
            expInput.value = cashTotal;
            toast(`💡 Expected cash auto-calculated: ${inr(cashTotal)}`);
          } catch (err) {
            console.error("Auto cash closing calc failed:", err);
          }
        };
      }
    }, 100);
  }

  f.onsubmit = async e => {
    e.preventDefault();

    // Check and upload file for purchases or expenses
    const fileInput = document.getElementById("fi_bill") || document.getElementById("fi_bill_photo");
    if (fileInput && fileInput.files.length > 0) {
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      try {
        const uploadRes = await fetch("/api/upload", { method: "POST", body: formData });
        if (!uploadRes.ok) throw new Error("Upload failed. Allowed formats: JPG, PNG, PDF, TXT, CSV");
        const uploadData = await uploadRes.json();
        const hiddenInput = document.getElementById("f_bill") || document.getElementById("f_bill_photo");
        if (hiddenInput) hiddenInput.value = uploadData.url;
      } catch (uploadErr) {
        toast("⚠️ " + uploadErr.message);
        return;
      }
    }

    const data = {};
    new FormData(f).forEach((v, k) => { data[k] = v === "" ? null : v; });

    try {
      if (row) {
        await api("/api/data/" + t + "/" + row.id, { method: "PUT", body: data });
        toast("✏️ Entry updated successfully");
      } else {
        await api("/api/data/" + t, { method: "POST", body: data });
        toast("✅ Entry created successfully");
      }
      m.classList.remove("on");
      if (typeof invalidate === "function") invalidate(t);
      list(t);
    } catch (err) {
      toast("⚠️ " + err.message);
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

function setView(html, my) {
  if (my !== undefined && my !== NAV) return false;
  const v = $("#view"); v.innerHTML = html; v.classList.remove("in"); void v.offsetWidth; v.classList.add("in"); return true;
}

function skel(n = 5) { return '<div class="card">' + '<div class="skel"></div>'.repeat(n) + "</div>"; }

function dskel() { return '<div class="kpis">' + '<div class="card skel" style="height:86px;margin:0"></div>'.repeat(6) + '</div><div class="grid">' + '<div class="card skel" style="height:286px;margin:0"></div>'.repeat(2) + "</div>"; }

function pwField(id, auto = "new-password") { return '<div class="pw"><input id="' + id + '" type="password" autocomplete="' + auto + '" required><button type="button" class="eye" aria-label="Show password" onclick="togglePw(this)">👁</button></div>'; }

function togglePw(b) { const i = b.previousElementSibling, show = i.type === "password"; i.type = show ? "text" : "password"; b.textContent = show ? "🙈" : "👁"; b.setAttribute("aria-label", show ? "Hide password" : "Show password"); }

function showShell(on) {
  document.body.classList.remove("booting"); const sp = $("#splash"); if (sp) sp.remove();
  $("#side").style.display = on ? "flex" : "none"; $("#burger").style.display = "";
}

function pager(el, d, go) {
  if (!el) return;
  el.innerHTML = '<span class="mu small">' + d.total + " entries · page " + d.page + " of " + d.pages + '</span><button class="s" ' + (d.page <= 1 ? "disabled" : "") + ' data-g="' + (d.page - 1) + '">← Prev</button><button class="s" ' + (d.page >= d.pages ? "disabled" : "") + ' data-g="' + (d.page + 1) + '">Next →</button>';
  el.querySelectorAll("[data-g]").forEach(b => b.onclick = () => go(+b.dataset.g));
}

function isAllAccess() { return CURRENT_USER.role === "owner" || CURRENT_USER.role === "superadmin" || (CURRENT_USER.allowed_sections || []).includes("*"); }

function homePage() {
  const a = CURRENT_USER.allowed_sections || [];
  if (isAllAccess() || a.includes("dashboard")) return "dashboard";
  return Object.keys(SCHEMA).find(k => a.includes(k)) || "none";
}

function passwordModal(force) {
  const m = $("#modal"), f = $("#form");
  f.innerHTML = "<h3>" + (force ? "Set your new password" : "Change password") + "</h3>" + (force ? '<p class="mu small">Your temporary password must be replaced before you continue.</p>' : "") +
    '<label>Current password</label>' + pwField("pw_cur", "current-password") + "<label>New password (8+ characters)</label>" + pwField("pw_new") + "<label>Confirm new password</label>" + pwField("pw_new2") +
    '<div id="pw_err" class="bad small" role="alert" style="min-height:18px"></div><div class="row">' + (force ? "" : '<button type="button" onclick="closeModal()">Cancel</button>') + '<button class="p">Save password</button></div>';
  m.classList.add("on");
  f.onsubmit = async e => {
    e.preventDefault(); if ($("#pw_new").value !== $("#pw_new2").value) { $("#pw_err").textContent = "The new passwords do not match."; return; }
    try { await api("/api/auth/change-password", { method: "POST", body: { current: $("#pw_cur").value, new: $("#pw_new").value } }); CURRENT_USER.must_set_password = false; closeModal(); toast("Password updated"); route(); }
    catch (ex) { $("#pw_err").textContent = ex.message; }
  };
}

function accessFields(meta, secs, tiles) {
  const sx = new Set(secs), tx = new Set(tiles);
  return '<label>Section access</label><div class="chk-list">' + meta.sections.map(s => '<label class="chk"><span>' + (ICONS[s.key] || "📄") + " <strong>" + esc(s.label) + '</strong></span><input type="checkbox" data-sec="' + s.key + '"' + (sx.has(s.key) ? " checked" : "") + "></label>").join("") +
    '</div><div id="tile-box" class="tile-box"' + (sx.has("dashboard") ? "" : " hidden") + '><label>Dashboard tiles this person can see <a href="#" id="tile-all">select all / none</a></label><div class="chk-list">' +
    meta.tiles.map(t => '<label class="chk"><span>' + esc(t.label) + '</span><input type="checkbox" data-tile="' + t.key + '"' + (tx.has(t.key) ? " checked" : "") + "></label>").join("") + "</div></div>";
}

function wireAccess(f) {
  const d = f.querySelector('[data-sec="dashboard"]'), box = f.querySelector("#tile-box");
  d.onchange = () => { box.hidden = !d.checked; };
  f.querySelector("#tile-all").onclick = e => { e.preventDefault(); const c = [...box.querySelectorAll("[data-tile]")], all = c.every(x => x.checked); c.forEach(x => x.checked = !all); };
}

function readAccess(f) { return { allowed_sections: [...f.querySelectorAll("[data-sec]:checked")].map(x => x.dataset.sec), allowed_tiles: [...f.querySelectorAll("[data-tile]:checked")].map(x => x.dataset.tile) }; }

function editAccess(u, meta) {
  const m = $("#modal"), f = $("#form"), secs = u.allowed_sections.includes("*") ? meta.sections.map(s => s.key) : u.allowed_sections;
  f.innerHTML = "<h3>Access for " + esc(u.username) + "</h3>" + accessFields(meta, secs, u.effective_tiles) + '<div class="row"><button type="button" onclick="closeModal()">Cancel</button><button class="p">Save access</button></div>';
  m.classList.add("on"); wireAccess(f);
  f.onsubmit = async e => { e.preventDefault(); try { await api("/api/users/" + u.id + "/permissions", { method: "PUT", body: readAccess(f) }); closeModal(); toast("Access updated for " + u.username); settings(); } catch (err) { toast(err.message); } };
}

function addMember(meta) {
  const m = $("#modal"), f = $("#form");
  f.innerHTML = '<h3>Add team member</h3><label>Username</label><input id="nu_name" required minlength="3" autocomplete="off"><label>Temporary password (8+ characters)</label>' + pwField("nu_pass") +
    '<div class="mu small" style="margin-top:4px">They must choose their own password at first sign-in. <a href="#" id="gen">Generate one</a></div><label>Role</label><select id="nu_role">' +
    meta.roles.map(r => '<option value="' + esc(r) + '"' + (r === "cashier" ? " selected" : "") + ">" + esc(cap(r)) + "</option>").join("") + '<option value="__new">➕ Add new role…</option></select>' +
    '<input id="nu_newrole" placeholder="New role name, e.g. Head Chef" maxlength="30" hidden style="margin-top:6px">' + accessFields(meta, PRESETS.cashier, meta.tiles.map(t => t.key)) +
    '<div class="row"><button type="button" onclick="closeModal()">Cancel</button><button class="p">Create member</button></div>';
  m.classList.add("on"); wireAccess(f);
  $("#gen").onclick = e => { e.preventDefault(); const c = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789", a = crypto.getRandomValues(new Uint32Array(10)); const p = $("#nu_pass"); p.value = [...a].map(n => c[n % c.length]).join(""); p.type = "text"; };
  $("#nu_role").onchange = e => {
    $("#nu_newrole").hidden = e.target.value !== "__new";
    const pre = PRESETS[e.target.value]; if (!pre) return;
    f.querySelectorAll("[data-sec]").forEach(x => x.checked = pre.includes(x.dataset.sec)); $("#tile-box").hidden = !pre.includes("dashboard");
  };
  f.onsubmit = async e => {
    e.preventDefault(); const sel = $("#nu_role").value, role = sel === "__new" ? $("#nu_newrole").value : sel;
    try { await api("/api/users", { method: "POST", body: { username: $("#nu_name").value, password: $("#nu_pass").value, role, ...readAccess(f) } }); closeModal(); toast("Team member created"); settings(); } catch (err) { toast(err.message); }
  };
}

async function memberAction(a, u, meta) {
  try {
    if (a === "edit") return editAccess(u, meta);
    if (a === "toggle") { await api("/api/users/" + u.id + "/active", { method: "PUT", body: { active: !u.is_active } }); toast(u.username + (u.is_active ? " deactivated" : " activated")); return settings(); }
    if (!confirm("Reset the password for " + u.username + "? They will be signed out everywhere.")) return;
    const r = await api("/api/users/" + u.id + "/reset-password", { method: "POST" }), m = $("#modal"), f = $("#form");
    f.innerHTML = "<h3>Temporary password for " + esc(u.username) + '</h3><p class="mu small">Share it privately. It is shown only once; ' + esc(u.username) + ' must replace it at next sign-in.</p><div class="pw"><input id="tp" type="password" readonly value="' + esc(r.password) + '"><button type="button" class="eye" aria-label="Show password" onclick="togglePw(this)">👁</button></div><div class="row"><button type="button" id="cp">Copy</button><button type="button" class="p" onclick="closeModal();settings()">Done</button></div>';
    m.classList.add("on"); f.onsubmit = e => e.preventDefault();
    $("#cp").onclick = () => navigator.clipboard.writeText(r.password).then(() => toast("Copied"));
  } catch (err) { toast(err.message); }
}

function teamTab(users, meta) {
  const rows = users.map(u => {
    const own = u.role === "owner" || u.role === "superadmin", id = ' data-id="' + u.id + '"';
    const secs = own ? '<span class="mu">Full access</span>' : (u.allowed_sections.map(s => '<span class="tag">' + (ICONS[s] || "") + " " + esc(s) + "</span>").join("") || '<span class="mu">No access</span>');
    const tl = !own && u.allowed_sections.includes("dashboard") ? '<div class="mu small">Dashboard tiles: ' + u.effective_tiles.length + " of " + meta.tiles.length + "</div>" : "";
    return '<tr class="' + (u.is_active ? "" : "off") + '"><td><strong>' + esc(u.username) + '</strong><div class="mu small">' + (u.is_active ? "" : "Deactivated · ") + (u.last_login_at ? "Last sign-in " + fmt(u.last_login_at) : "Never signed in") + '</div></td><td><span class="badge-role">' + esc(u.role) + "</span></td><td>" + secs + tl + "</td><td>" +
      (own ? '<span class="mu">Owner</span>' : '<button class="s p" data-a="edit"' + id + '>⚙️ Edit access</button> <button class="s" data-a="reset"' + id + '>🔑 Reset password</button> <button class="s ' + (u.is_active ? "d" : "") + '" data-a="toggle"' + id + ">" + (u.is_active ? "Deactivate" : "Activate") + "</button>") + "</td></tr>";
  }).join("");
  $("#tab").innerHTML = '<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;gap:8px;flex-wrap:wrap"><h3 style="margin:0">Active team logins & permissions</h3><button class="p s" id="add-user-btn">+ Add Team Member</button></div><div class="wrap"><table><thead><tr><th>Member</th><th>Role</th><th>Access</th><th>Actions</th></tr></thead><tbody>' + rows +
    '</tbody></table></div><p class="mu small" style="margin:12px 0 0">🔒 Passwords are stored as one-way hashes and can never be viewed, even by the owner. If someone forgets theirs, use <strong>Reset password</strong> to issue a temporary one.</p></div>';
  $("#add-user-btn").onclick = () => addMember(meta);
  document.querySelectorAll("[data-a]").forEach(b => b.onclick = () => memberAction(b.dataset.a, users.find(x => String(x.id) === b.dataset.id), meta));
}

function rolesTab(users, meta) {
  const used = r => users.filter(u => u.role === r).length;
  $("#tab").innerHTML = '<div class="card"><h3>Roles</h3><p class="mu small">Roles are labels for your team, such as Head Chef or Waiter. What each person can open is set by the access checkboxes on the Team tab.</p><table><tbody>' +
    meta.roles.map(r => '<tr><td><strong>' + esc(cap(r)) + '</strong></td><td class="mu">' + used(r) + " member(s)</td><td>" + (meta.builtin_roles.includes(r) ? '<span class="mu">Built-in</span>' : '<button class="s d" data-del="' + esc(r) + '">Delete</button>') + "</td></tr>").join("") +
    '</tbody></table><div class="tools" style="margin-top:12px"><input id="role_new" placeholder="New role name" maxlength="30" aria-label="New role name"><button class="p" id="role_add">Add role</button></div></div>';
  
  $("#role_add").onclick = async () => {
    const roleVal = $("#role_new").value.trim();
    if (!roleVal) {
      toast("Please enter a role name");
      return;
    }
    try {
      await api("/api/roles", { method: "POST", body: { name: roleVal } });
      toast("Role added successfully");
      settings("roles");
    } catch (e) {
      // Replaces any raw backend "superadmin" message with a clean notice
      const msg = e.message.replace(/superadmin/gi, "Owner");
      toast(msg);
    }
  };

  document.querySelectorAll("[data-del]").forEach(b => b.onclick = async () => {
    if (!confirm("Delete role " + b.dataset.del + "?")) return;
    try {
      await api("/api/roles/" + encodeURIComponent(b.dataset.del), { method: "DELETE" });
      toast("Role deleted successfully");
      settings("roles");
    } catch (e) {
      const msg = e.message.replace(/superadmin/gi, "Owner");
      toast(msg);
    }
  });
}

function logDetail(l) {
  const c = l.details && l.details.changes;
  return c ? Object.entries(c).map(([k, v]) => esc(k) + ": " + esc(v[0] ?? "–") + " → " + esc(v[1] ?? "–")).join(" · ") : "";
}

function logsTab(users) {
  const my = NAV;
  $("#tab").innerHTML = '<div class="card"><div class="tools"><select id="lg_user" aria-label="Member"><option value="">All members</option>' + users.map(u => '<option value="' + u.id + '"' + (LOGS.user === u.id ? " selected" : "") + ">" + esc(u.username) + "</option>").join("") +
    '</select><select id="lg_kind" aria-label="Action type">' + [["", "All actions"], ["create", "Added"], ["update", "Edited"], ["delete", "Deleted"], ["login", "Sign-ins"], ["user", "Team changes"], ["password", "Passwords"], ["role", "Roles"]].map(([v, l]) => '<option value="' + v + '"' + (LOGS.kind === v ? " selected" : "") + ">" + l + "</option>").join("") +
    '</select></div><div class="wrap"><table><thead><tr><th>When</th><th>Member</th><th>What happened</th><th>Changes</th></tr></thead><tbody id="lg_body"><tr><td colspan="4"><div class="skel"></div></td></tr></tbody></table></div><div id="lg_pg" class="pager"></div></div>';
  const load = async () => {
    try {
      const d = await api("/api/logs?page=" + LOGS.page + "&size=10&user_id=" + LOGS.user + "&kind=" + LOGS.kind); if (my !== NAV) return;
      $("#lg_body").innerHTML = d.rows.length ? d.rows.map(l => "<tr><td>" + fmt(l.created_at) + "</td><td><strong>" + esc(l.who) + "</strong></td><td>" + esc(l.action) + '</td><td class="mu small">' + logDetail(l) + "</td></tr>").join("") : '<tr><td colspan="4" class="mu" style="text-align:center;padding:24px">No activity found</td></tr>';
      pager($("#lg_pg"), d, p => { LOGS.page = p; load(); });
    } catch (e) { $("#lg_body").innerHTML = '<tr><td colspan="4" class="bad">' + esc(e.message) + "</td></tr>"; }
  };
  $("#lg_user").onchange = e => { LOGS.user = e.target.value; LOGS.page = 1; load(); };
  $("#lg_kind").onchange = e => { LOGS.kind = e.target.value; LOGS.page = 1; load(); };
  load();
}

function lookTab(users, meta) {
  const currentCurr = (meta && meta.currency) || APP_CURRENCY || "₹";

  $("#tab").innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <h3>Theme</h3>
      <p class="mu small">Saved on this device.</p>
      <div style="display:flex;gap:10px">
        <button data-th="light">☀️ Light</button>
        <button data-th="dark">🌙 Dark</button>
      </div>
    </div>

    <div class="card">
      <h3>Currency & Region</h3>
      <p class="mu small">Controls money formatting across tables, bills, and dashboard cards.</p>
      <div style="display:flex;gap:12px;align-items:center;margin-top:12px;max-width:320px">
        <select id="currency-select" style="flex:1;padding:8px;border-radius:6px;border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-weight:600">
          <option value="₹">₹ - Indian Rupee (INR)</option>
          <option value="$">$ - US Dollar (USD)</option>
          <option value="€">€ - Euro (EUR)</option>
          <option value="£">£ - British Pound (GBP)</option>
          <option value="AED">AED - UAE Dirham</option>
          <option value="SAR">SAR - Saudi Riyal</option>
        </select>
        <button id="save-currency-btn" class="p" style="white-space:nowrap;padding:8px 16px">Save</button>
      </div>
    </div>
  `;

  // Select the saved currency
  const selectEl = $("#currency-select");
  if (selectEl) {
    selectEl.value = currentCurr;
  }

  // Theme switch handlers
  document.querySelectorAll("[data-th]").forEach(b => b.onclick = () => {
    document.documentElement.setAttribute("data-theme", b.dataset.th);
    localStorage.setItem("theme", b.dataset.th);
    updateHeaderControls();
  });

  // Save currency handler
  const saveBtn = $("#save-currency-btn");
  if (saveBtn && selectEl) {
    // Re-enable button when user picks a different currency from the dropdown
    selectEl.onchange = () => {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save";
      saveBtn.style.background = "";
      saveBtn.style.opacity = "1";
      saveBtn.style.cursor = "pointer";
    };

    saveBtn.onclick = async () => {
      const selected = selectEl.value;
      try {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";
        saveBtn.style.opacity = "0.7";

        await api("/api/settings/currency", { method: "PUT", body: { currency: selected } });

        APP_CURRENCY = selected;
        localStorage.setItem("app_currency", selected);
        if (meta) meta.currency = selected;

        toast("✅ Currency updated to " + selected);

        // Turn green and show confirmation state
        saveBtn.textContent = "✓ Saved";
        saveBtn.style.background = "#16a34a";
        saveBtn.style.opacity = "1";
        saveBtn.style.cursor = "default";
        saveBtn.disabled = true;

        // Re-render views if route exists
        if (typeof route === "function") route();
      } catch (err) {
        toast("⚠️ " + (err.message || "Failed to update currency"));
        saveBtn.disabled = false;
        saveBtn.textContent = "Save";
        saveBtn.style.background = "";
        saveBtn.style.opacity = "1";
        saveBtn.style.cursor = "pointer";
      }
    };
  }
}
init();
