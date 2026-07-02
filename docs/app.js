/* AI Toolkit by Role — filterable directory. Vanilla JS, no dependencies. */
(function () {
  "use strict";

  const state = {
    q: "",
    sort: "stars",
    roles: new Set(),
    surfaces: new Set(),
    types: new Set(),
    tools: new Set(),
  };
  const kfmt = (n) => (n == null ? "" : n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n));
  let DATA = null;
  let toolLabel = {}, typeById = {}, surfaceById = {};

  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  async function init() {
    try {
      DATA = await (await fetch("data.json")).json();
    } catch (e) {
      $("grid").innerHTML = '<p class="empty">Could not load data.json.</p>';
      return;
    }
    toolLabel = Object.fromEntries(DATA.tools.map((t) => [t.id, t.label]));
    typeById = Object.fromEntries(DATA.types.map((t) => [t.id, t]));
    surfaceById = Object.fromEntries(DATA.surfaces.map((s) => [s.id, s]));

    renderBadges();
    renderDefs();
    renderChips();
    renderCollections();
    preselectFromURL();

    $("search").addEventListener("input", (e) => {
      state.q = e.target.value.trim().toLowerCase();
      render();
    });
    $("sort").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
    $("clear").addEventListener("click", clearAll);
    render();
  }

  function renderCollections() {
    const colls = (DATA.collections || []).filter((c) => c.kind === "collection");
    const markets = (DATA.collections || []).filter((c) => c.kind === "marketplace");
    const cg = $("collGrid");
    colls.forEach((c) => {
      const a = el("a", "coll-card");
      a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      const h = el("div", "coll-top");
      h.appendChild(el("span", "coll-name", c.name + (c.official ? " ✓" : "")));
      if (c.stars) h.appendChild(el("span", "coll-stars", "⭐ " + kfmt(c.stars)));
      a.appendChild(h);
      a.appendChild(el("p", "coll-what", c.what));
      cg.appendChild(a);
    });
    const ml = $("marketList");
    markets.forEach((c) => {
      const a = el("a", "market-item");
      a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      a.appendChild(el("span", "market-name", c.name));
      a.appendChild(el("span", "market-what", c.what));
      ml.appendChild(a);
    });
  }

  function renderBadges() {
    const s = DATA.stats;
    const row = $("badgeRow");
    const items = [
      `${s.total} tools`,
      `${s.by_type.skill} skills`,
      `${s.by_type.connector} connectors`,
      `${Object.values(s.by_role).filter(Boolean).length} roles`,
      `updated ${DATA.generated_at}`,
    ];
    items.forEach((t) => row.appendChild(el("span", "pill", t)));
  }

  function renderDefs() {
    const td = $("typeDefs");
    DATA.types.forEach((t) => {
      const p = el("p", "def");
      p.innerHTML = `<b>${t.emoji} ${escapeHtml(t.label)}</b> — ${escapeHtml(t.description)}`;
      td.appendChild(p);
    });
    const sd = $("surfaceDefs");
    DATA.surfaces.forEach((s) => {
      const p = el("p", "def");
      p.innerHTML = `<b>${s.emoji} ${escapeHtml(s.label)}</b> — ${escapeHtml(s.description)}`;
      sd.appendChild(p);
    });
  }

  function chip(container, id, label, group) {
    const b = el("button", "chip", label);
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => {
      const set = state[group];
      if (set.has(id)) { set.delete(id); b.setAttribute("aria-pressed", "false"); }
      else { set.add(id); b.setAttribute("aria-pressed", "true"); }
      render();
    });
    b.dataset.group = group;
    b.dataset.id = id;
    container.appendChild(b);
  }

  function renderChips() {
    DATA.roles.forEach((r) => chip($("roleChips"), r.id, `${r.emoji} ${r.label}`, "roles"));
    DATA.surfaces.forEach((s) => chip($("surfaceChips"), s.id, `${s.emoji} ${s.label}`, "surfaces"));
    DATA.types.forEach((t) => chip($("typeChips"), t.id, `${t.emoji} ${t.label}`, "types"));
    DATA.tools.forEach((t) => chip($("toolChips"), t.id, t.label, "tools"));
  }

  function preselectFromURL() {
    const role = new URLSearchParams(location.search).get("role");
    if (role && DATA.roles.some((r) => r.id === role)) {
      state.roles.add(role);
      const b = document.querySelector(`.chip[data-group="roles"][data-id="${role}"]`);
      if (b) b.setAttribute("aria-pressed", "true");
    }
  }

  function surfaceMatch(item) {
    if (state.surfaces.size === 0) return true;
    if (state.surfaces.has(item.surface)) return true;
    // an item that works in BOTH also satisfies a chat-only or code-only filter
    return item.surface === "both" && (state.surfaces.has("chat") || state.surfaces.has("code"));
  }

  function matches(item) {
    if (state.roles.size && !item.roles.some((r) => state.roles.has(r))) return false;
    if (!surfaceMatch(item)) return false;
    if (state.types.size && !state.types.has(item.type)) return false;
    if (state.tools.size && !item.tools.some((t) => state.tools.has(t))) return false;
    if (state.q) {
      const hay = (item.name + " " + item.what + " " + item.why + " " + item.tags.join(" ")).toLowerCase();
      if (!hay.includes(state.q)) return false;
    }
    return true;
  }

  function card(item) {
    const c = el("div", "card");
    const top = el("div", "card-top");
    const h = el("h3");
    const a = el("a", null, item.name);
    a.href = item.docs; a.target = "_blank"; a.rel = "noopener";
    h.appendChild(a);
    top.appendChild(h);
    const meta = el("div", "card-meta");
    if (item.stars) meta.appendChild(el("span", "stars", "⭐ " + kfmt(item.stars)));
    if (item.official) meta.appendChild(el("span", "official", "✓"));
    top.appendChild(meta);
    c.appendChild(top);

    const tags = el("div", "tags-row");
    const ty = typeById[item.type], su = surfaceById[item.surface];
    tags.appendChild(el("span", `tag type-${item.type}`, `${ty.emoji} ${ty.label}`));
    tags.appendChild(el("span", `tag surface-${item.surface}`, `${su.emoji} ${su.label}`));
    tags.appendChild(el("span", "tag", item.difficulty));
    if (item.built_in) tags.appendChild(el("span", "tag builtin", "🧰 built-in"));
    c.appendChild(tags);

    c.appendChild(el("p", "what", item.what));
    c.appendChild(el("p", "why", item.why));

    const foot = el("div", "card-foot");
    item.tools.forEach((t) => foot.appendChild(el("span", "tool-badge", toolLabel[t] || t)));
    c.appendChild(foot);
    return c;
  }

  function render() {
    const grid = $("grid");
    grid.innerHTML = "";
    const results = DATA.items.filter(matches);
    $("count").textContent = `${results.length} of ${DATA.items.length} tools`;
    if (results.length === 0) {
      grid.innerHTML = '<p class="empty">No tools match those filters. Try clearing some.</p>';
      return;
    }
    const cmp = {
      stars: (a, b) => (b.stars || 0) - (a.stars || 0) || a.name.localeCompare(b.name),
      beginner: (a, b) => (a.difficulty !== "beginner") - (b.difficulty !== "beginner") || (b.stars || 0) - (a.stars || 0),
      name: (a, b) => a.name.localeCompare(b.name),
    };
    results.sort(cmp[state.sort] || cmp.stars).forEach((it) => grid.appendChild(card(it)));
  }

  function clearAll() {
    state.q = "";
    ["roles", "surfaces", "types", "tools"].forEach((g) => state[g].clear());
    $("search").value = "";
    document.querySelectorAll('.chip[aria-pressed="true"]').forEach((b) => b.setAttribute("aria-pressed", "false"));
    render();
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  }

  document.addEventListener("DOMContentLoaded", init);
})();
