/* 搜索记录 — localStorage 持久化 + 列表 UI（仅存 intent，不存 search_id） */
(function () {
  const STORAGE_KEY = "fm_nl_search_history";
  const MAX_ITEMS = 30;
  /** 历史条目禁止携带运行时 search 标识，避免再次搜索误走旧 stream */
  const STRIP_HISTORY_KEYS = ["searchId", "search_id", "stream_nonce", "stream_url"];

  function sanitizeRecord(item) {
    if (!item || typeof item !== "object") return item;
    const clean = { ...item };
    for (const k of STRIP_HISTORY_KEYS) delete clean[k];
    return clean;
  }

  function loadAll() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const list = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(list)) return [];
      const sanitized = list.map(sanitizeRecord);
      if (JSON.stringify(sanitized) !== JSON.stringify(list)) {
        persist(sanitized);
      }
      return sanitized;
    } catch (_) {
      return [];
    }
  }

  function persist(list) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, MAX_ITEMS)));
    } catch (_) {}
  }

  function formatTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function joinLabels(codes, labels) {
    return (codes || [])
      .map((c) => labels?.[c] || c)
      .filter(Boolean)
      .join("、");
  }

  function buildSummary(record) {
    if (record.summary) return record.summary;
    const intent = record.intent || {};
    const originLabels = record.originLabels || intent.origin_labels || {};
    const destLabels = record.destLabels || intent.dest_labels || {};
    if (record.kind === "matrix") {
      const o = joinLabels(intent.origins, originLabels);
      const d = joinLabels(intent.destinations, destLabels);
      const out = intent.out_date_start || intent.out_date || "";
      const ret = intent.ret_date_end || intent.ret_date || intent.out_date_end || "";
      return `矩阵 · ${o || "—"} → ${d || "—"} · ${out}${ret && ret !== out ? `~${ret}` : ""}`;
    }
    if (window.IntentQuery?.intentToQueryString) {
      const q = window.IntentQuery.intentToQueryString(intent, { originLabels, destLabels });
      if (q) {
        return record.searchMode === "exhaustive" ? `${q} · 全量穷举` : q;
      }
    }
    return record.nlQuery || "搜索记录";
  }

  function add(record) {
    const list = loadAll();
    const sanitized = sanitizeRecord(record);
    const entry = {
      id: sanitized.id || `hist_${Date.now().toString(36)}`,
      kind: sanitized.kind || "standard",
      searchMode: sanitized.searchMode || "smart",
      intent: sanitized.intent,
      originLabels: sanitized.originLabels || {},
      destLabels: sanitized.destLabels || {},
      dateMode: sanitized.dateMode || "range",
      nlQuery: sanitized.nlQuery || "",
      summary: sanitized.summary || buildSummary(sanitized),
      createdAt: sanitized.createdAt || new Date().toISOString(),
    };
    const deduped = list.filter(
      (item) =>
        !(
          item.kind === entry.kind &&
          item.searchMode === entry.searchMode &&
          JSON.stringify(item.intent) === JSON.stringify(entry.intent)
        )
    );
    deduped.unshift(entry);
    persist(deduped);
    renderPanel();
    return entry;
  }

  function remove(id) {
    persist(loadAll().filter((item) => item.id !== id));
    renderPanel();
  }

  function clearAll() {
    persist([]);
    renderPanel();
  }

  function list() {
    return loadAll();
  }

  function handleHistoryClick(e) {
    const rerunBtn = e.target.closest(".search-history-rerun");
    const loadBtn = e.target.closest(".search-history-load");
    const removeBtn = e.target.closest(".search-history-remove");
    const btn = rerunBtn || loadBtn || removeBtn;
    if (!btn?.dataset.id) return;
    const item = loadAll().find((x) => x.id === btn.dataset.id);
    if (!item) return;
    if (removeBtn) {
      remove(btn.dataset.id);
      return;
    }
    void window.SearchHistoryBridge?.rerun(item, { autoSearch: Boolean(rerunBtn) });
  }

  function bindHistoryPanel() {
    const listEl = document.getElementById("searchHistoryList");
    if (!listEl || listEl.dataset.bound === "1") return;
    listEl.dataset.bound = "1";
    listEl.addEventListener("click", handleHistoryClick);
  }

  function renderPanel() {
    const section = document.getElementById("searchHistorySection");
    const listEl = document.getElementById("searchHistoryList");
    const emptyEl = document.getElementById("searchHistoryEmpty");
    if (!section || !listEl) return;

    bindHistoryPanel();

    const items = loadAll();
    section.classList.toggle("hidden", !items.length);
    if (!items.length) {
      listEl.innerHTML = "";
      if (emptyEl) emptyEl.classList.add("hidden");
      return;
    }

    listEl.innerHTML = items
      .map((item) => {
        const kindLabel = item.kind === "matrix" ? "矩阵" : item.searchMode === "exhaustive" ? "全量" : "精简";
        const summary = buildSummary(item);
        return `
          <li class="search-history-item" data-id="${item.id}">
            <div class="search-history-main">
              <span class="search-history-badge">${kindLabel}</span>
              <span class="search-history-summary" title="${summary.replace(/"/g, "&quot;")}">${summary}</span>
              <span class="search-history-time">${formatTime(item.createdAt)}</span>
            </div>
            <div class="search-history-actions">
              <button type="button" class="btn btn-ghost btn-sm search-history-rerun" data-id="${item.id}">再次搜索</button>
              <button type="button" class="btn btn-ghost btn-sm search-history-load" data-id="${item.id}">加载条件</button>
              <button type="button" class="btn btn-ghost btn-sm search-history-remove" data-id="${item.id}" title="删除">×</button>
            </div>
          </li>`;
      })
      .join("");
  }

  window.SearchHistory = {
    add,
    list,
    remove,
    clear: clearAll,
    buildSummary,
    renderPanel,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderPanel);
  } else {
    renderPanel();
  }

  document.getElementById("btnClearSearchHistory")?.addEventListener("click", () => {
    if (confirm("确定清空全部搜索记录？")) clearAll();
  });
})();
