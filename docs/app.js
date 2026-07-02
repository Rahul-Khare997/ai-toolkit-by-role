/* AI Toolkit by Role — filterable directory + install cart. Vanilla JS, no deps. */
(function () {
  "use strict";

  const LS_KEY = "aitk-cart";
  const state = {
    q: "", sort: "stars",
    roles: new Set(), surfaces: new Set(), types: new Set(), tools: new Set(),
    cart: new Set(), cartTool: null,
  };
  const kfmt = (n) => (n == null ? "" : n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n));
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let DATA = null, toolLabel = {}, typeById = {}, surfaceById = {}, io = null;

  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const esc = (s) => String(s).replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));

  async function init() {
    try { DATA = await (await fetch("data.json")).json(); }
    catch (e) { $("grid").innerHTML = '<p class="empty">Could not load data.json.</p>'; return; }
    toolLabel = Object.fromEntries(DATA.tools.map((t) => [t.id, t.label]));
    typeById = Object.fromEntries(DATA.types.map((t) => [t.id, t]));
    surfaceById = Object.fromEntries(DATA.surfaces.map((s) => [s.id, s]));
    loadCart();

    io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -40px 0px" });

    renderStats();
    renderDefs();
    renderChips();
    renderCollections();
    preselectFromURL();

    $("tray").hidden = false; $("toast").hidden = false;
    $("search").addEventListener("input", (e) => { state.q = e.target.value.trim().toLowerCase(); render(); });
    $("sort").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
    $("clear").addEventListener("click", clearFilters);
    $("selectAll").addEventListener("click", selectAllShown);
    $("trayClear").addEventListener("click", () => { state.cart.clear(); saveCart(); render(); updateTray(); });
    $("trayTool").addEventListener("change", (e) => { state.cartTool = e.target.value; updateTray(); });
    $("copyPrompt").addEventListener("click", () => copy(buildPrompt(), `Copied AI prompt for ${state.cart.size} tool(s)`));
    $("copyCommands").addEventListener("click", () => copy(buildCommands(), `Copied commands for ${state.cart.size} tool(s)`));

    render();
    updateTray();
  }

  /* ---------- count-up hero stats ---------- */
  function renderStats() {
    const s = DATA.stats;
    const defs = [
      { n: s.total, l: "AI tools", accent: false },
      { n: s.with_stars, l: "with live ⭐", accent: true },
      { n: Object.values(s.by_role).filter(Boolean).length, l: "roles", accent: false },
      { n: (DATA.collections || []).length, l: "places to find more", accent: false },
    ];
    const row = $("statRow");
    defs.forEach((d) => {
      const box = el("div", "stat");
      const num = el("div", "num" + (d.accent ? " accent" : ""), reduce ? String(d.n) : "0");
      box.appendChild(num); box.appendChild(el("div", "lbl", d.l));
      row.appendChild(box);
      if (!reduce) countUp(num, d.n, 900);
    });
  }
  function countUp(node, target, ms) {
    const start = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - start) / ms);
      node.textContent = String(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function renderDefs() {
    DATA.types.forEach((t) => { const p = el("p", "def"); p.innerHTML = `<b>${t.emoji} ${esc(t.label)}</b> — ${esc(t.description)}`; $("typeDefs").appendChild(p); });
    DATA.surfaces.forEach((s) => { const p = el("p", "def"); p.innerHTML = `<b>${s.emoji} ${esc(s.label)}</b> — ${esc(s.description)}`; $("surfaceDefs").appendChild(p); });
  }

  function chip(container, id, label, group) {
    const b = el("button", "chip", label);
    b.setAttribute("aria-pressed", "false");
    b.dataset.group = group; b.dataset.id = id;
    b.addEventListener("click", () => {
      const set = state[group];
      const on = !set.has(id);
      on ? set.add(id) : set.delete(id);
      b.setAttribute("aria-pressed", String(on));
      render();
    });
    container.appendChild(b);
  }
  function renderChips() {
    DATA.roles.forEach((r) => chip($("roleChips"), r.id, `${r.emoji} ${r.label}`, "roles"));
    DATA.surfaces.forEach((s) => chip($("surfaceChips"), s.id, `${s.emoji} ${s.label}`, "surfaces"));
    DATA.types.forEach((t) => chip($("typeChips"), t.id, `${t.emoji} ${t.label}`, "types"));
    DATA.tools.forEach((t) => chip($("toolChips"), t.id, t.label, "tools"));
  }

  function renderCollections() {
    const colls = (DATA.collections || []).filter((c) => c.kind === "collection");
    const markets = (DATA.collections || []).filter((c) => c.kind === "marketplace");
    colls.forEach((c) => {
      const a = el("a", "coll-card"); a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      const h = el("div", "coll-top");
      h.appendChild(el("span", "coll-name", c.name + (c.official ? " ✓" : "")));
      if (c.stars) h.appendChild(el("span", "coll-stars", "⭐ " + kfmt(c.stars)));
      a.appendChild(h); a.appendChild(el("p", "coll-what", c.what));
      $("collGrid").appendChild(a);
    });
    markets.forEach((c) => {
      const a = el("a", "market-item"); a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      a.appendChild(el("span", "market-name", c.name));
      a.appendChild(el("span", "market-what", c.what));
      $("marketList").appendChild(a);
    });
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

  function card(item, index) {
    const c = el("div", "card"); c.dataset.id = item.id;
    if (state.cart.has(item.id)) c.classList.add("selected");
    c.style.transitionDelay = reduce ? "0ms" : Math.min(index * 28, 280) + "ms";

    const pick = el("input", "pick");
    pick.type = "checkbox"; pick.checked = state.cart.has(item.id);
    pick.setAttribute("aria-label", "Select " + item.name + " to install");
    pick.addEventListener("change", () => toggleCart(item.id, c, pick.checked));
    c.appendChild(pick);

    const top = el("div", "card-top");
    const h = el("h3"); const a = el("a", null, item.name);
    a.href = item.docs; a.target = "_blank"; a.rel = "noopener"; h.appendChild(a); top.appendChild(h);
    const meta = el("div", "card-meta");
    if (item.stars) meta.appendChild(el("span", "stars", "⭐ " + kfmt(item.stars)));
    if (item.official) meta.appendChild(el("span", "official", "✓"));
    top.appendChild(meta); c.appendChild(top);

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
    const grid = $("grid"); grid.innerHTML = "";
    const results = DATA.items.filter(matches);
    $("count").textContent = `${results.length} of ${DATA.items.length} tools`;
    if (results.length === 0) { grid.innerHTML = '<p class="empty">No tools match those filters. Try clearing some.</p>'; return; }
    const cmp = {
      stars: (a, b) => (b.stars || 0) - (a.stars || 0) || a.name.localeCompare(b.name),
      beginner: (a, b) => (a.difficulty !== "beginner") - (b.difficulty !== "beginner") || (b.stars || 0) - (a.stars || 0),
      name: (a, b) => a.name.localeCompare(b.name),
    };
    results.sort(cmp[state.sort] || cmp.stars).forEach((it, i) => {
      const c = card(it, i); grid.appendChild(c);
      if (reduce) c.classList.add("in"); else io.observe(c);
    });
  }

  /* ---------- cart ---------- */
  function toggleCart(id, cardEl, on) {
    on ? state.cart.add(id) : state.cart.delete(id);
    if (cardEl) cardEl.classList.toggle("selected", on);
    saveCart(); updateTray();
  }
  function selectedItems() { return DATA.items.filter((i) => state.cart.has(i.id)); }

  function availableTools() {
    const ids = new Set();
    selectedItems().forEach((i) => Object.keys(i.install || {}).forEach((k) => ids.add(k)));
    let list = DATA.tools.filter((t) => ids.has(t.id));
    if (!list.length) { // fall back to tools the items run in
      const t2 = new Set(); selectedItems().forEach((i) => i.tools.forEach((t) => t2.add(t)));
      list = DATA.tools.filter((t) => t2.has(t.id));
    }
    return list;
  }

  function updateTray() {
    const tray = $("tray");
    const n = state.cart.size;
    if (n === 0) { tray.classList.remove("open"); return; }
    $("trayCount").textContent = `${n} selected`;

    // chips
    const chips = $("trayChips"); chips.innerHTML = "";
    selectedItems().forEach((i) => {
      const chipEl = el("span", "tray-chip", i.name);
      const x = el("button", null, "×"); x.setAttribute("aria-label", "Remove " + i.name);
      x.addEventListener("click", () => {
        state.cart.delete(i.id); saveCart();
        const cd = document.querySelector(`.card[data-id="${CSS.escape(i.id)}"]`);
        if (cd) { cd.classList.remove("selected"); const pk = cd.querySelector(".pick"); if (pk) pk.checked = false; }
        updateTray();
      });
      chipEl.appendChild(x); chips.appendChild(chipEl);
    });

    // tool picker
    const tools = availableTools();
    if (!state.cartTool || !tools.some((t) => t.id === state.cartTool)) state.cartTool = (tools[0] || {}).id || "claude-code";
    const sel = $("trayTool"); sel.innerHTML = "";
    tools.forEach((t) => { const o = el("option", null, t.label); o.value = t.id; if (t.id === state.cartTool) o.selected = true; sel.appendChild(o); });

    // skip note
    const skipped = selectedItems().filter((i) => !(i.install && i.install[state.cartTool]));
    $("traySkip").textContent = skipped.length
      ? `⚠ ${skipped.length} of ${n} have no ${toolLabel[state.cartTool]} step — copy still includes them with a docs link: ${skipped.map((i) => i.name).join(", ")}`
      : "";

    tray.classList.add("open");
  }

  function buildPrompt() {
    const t = state.cartTool, label = toolLabel[t] || t, items = selectedItems();
    const supported = items.filter((i) => i.install && i.install[t]);
    const skipped = items.filter((i) => !(i.install && i.install[t]));
    let lines = supported.map((i, idx) => `${idx + 1}. ${i.name} — ${i.install[t]}  (docs: ${i.docs})`);
    let text = `Please help me install these AI tools in ${label}. For each one, apply the install step below; open the docs link if you need more detail. Confirm each before moving on.\n\n${lines.join("\n")}`;
    if (skipped.length) {
      const extra = skipped.map((i, idx) => `${supported.length + idx + 1}. ${i.name} — see docs: ${i.docs}`);
      text += `\n\nThese don't list a ${label} command — set them up from their docs:\n${extra.join("\n")}`;
    }
    return text;
  }
  function buildCommands() {
    const t = state.cartTool, label = toolLabel[t] || t;
    const cmds = selectedItems().filter((i) => i.install && i.install[t]).map((i) => `# ${i.name}\n${i.install[t]}`);
    return `# Install for ${label} — generated by AI Toolkit by Role\n\n${cmds.join("\n\n")}`;
  }

  function copy(text, msg) {
    const done = () => toast(msg);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
    } else fallbackCopy(text, done);
  }
  function fallbackCopy(text, done) {
    const ta = el("textarea"); ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); done(); } catch (e) { toast("Couldn't copy — try again"); }
    document.body.removeChild(ta);
  }
  let toastTimer = null;
  function toast(msg) {
    const t = $("toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 2400);
  }

  function selectAllShown() {
    DATA.items.filter(matches).forEach((i) => state.cart.add(i.id));
    saveCart(); render(); updateTray();
    toast(`Added ${state.cart.size} to the install cart`);
  }
  function clearFilters() {
    state.q = "";
    ["roles", "surfaces", "types", "tools"].forEach((g) => state[g].clear());
    $("search").value = "";
    document.querySelectorAll('.chip[aria-pressed="true"]').forEach((b) => b.setAttribute("aria-pressed", "false"));
    render();
  }

  function saveCart() { try { localStorage.setItem(LS_KEY, JSON.stringify([...state.cart])); } catch (e) {} }
  function loadCart() {
    try {
      const ids = JSON.parse(localStorage.getItem(LS_KEY) || "[]");
      const valid = new Set(DATA.items.map((i) => i.id));
      ids.forEach((id) => { if (valid.has(id)) state.cart.add(id); });
    } catch (e) {}
  }

  document.addEventListener("DOMContentLoaded", init);
})();
