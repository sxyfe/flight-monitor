/* 同步自 flight-monitor-agent/templates/report/report.js — 导出 ReportApp.init */
/* flight-monitor-agent 暖色报告 — 筛选、图表、排序、分页 */

const CHART_COLORS = [
  "#0d6e6e", "#e85d3b", "#2a9d8f", "#c9a227", "#6b4c9a",
  "#3d8b7a", "#d4694a", "#5b7fb8", "#8b6914", "#7a5c8a",
];

const state = {
  raw: null,
  offers: [],
  destMap: {},
  countryMap: {},
  cityLabels: {},
  priceBuckets: [],
  filters: {
    trip: "all",
    countries: new Set(),
    dests: new Set(),
    origins: new Set(),
    priceMin: 0,
    priceMax: 0,
    bucket: null,
  },
  sortBy: "price-asc",
  page: 1,
  pageSize: 50,
  charts: {},
};

function roundPriceStep(span, count = 5) {
  if (span <= 0) return 50;
  const raw = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  let step = mag;
  if (norm <= 1) step = mag;
  else if (norm <= 2) step = 2 * mag;
  else if (norm <= 5) step = 5 * mag;
  else step = 10 * mag;
  return Math.max(50, Math.round(step / 50) * 50);
}

function buildPriceBuckets(pMin, pMax) {
  if (!Number.isFinite(pMin) || !Number.isFinite(pMax)) return [];
  if (pMin >= pMax) {
    const v = Math.round(pMin);
    return [{ id: "b0", label: `¥${v}`, min: pMin, max: pMax }];
  }

  const step = roundPriceStep(pMax - pMin);
  let lo = Math.floor(pMin / step) * step;
  const buckets = [];
  let i = 0;

  while (lo <= pMax && i < 12) {
    const hi = lo + step - 1;
    const isLast = hi >= pMax;
    let label;
    if (i === 0 && lo < pMin) label = `< ¥${lo + step}`;
    else if (isLast) label = `≥ ¥${lo}`;
    else label = `¥${lo}–${hi}`;

    buckets.push({
      id: `b${i}`,
      label,
      min: i === 0 && lo < pMin ? 0 : lo,
      max: isLast ? Infinity : hi,
    });

    if (isLast) break;
    lo += step;
    i += 1;
  }

  return buckets;
}

function syncPriceBuckets() {
  if (!state.offers.length) {
    state.priceBuckets = [];
    return;
  }
  const prices = state.offers.map((o) => o.price);
  const pMin = Math.min(...prices);
  const pMax = Math.max(...prices);
  state.priceBuckets = buildPriceBuckets(pMin, pMax);
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildCityLabelsFromOffers(offers) {
  const labels = {};
  for (const o of offers) {
    if (o.origin && o.origin_name) labels[o.origin] = o.origin_name;
    if (o.ret_origin && o.ret_origin_name) labels[o.ret_origin] = o.ret_origin_name;
    if (o.out_dest && o.out_dest_name) labels[o.out_dest] = o.out_dest_name;
    if (o.ret_dest && o.ret_dest_name) labels[o.ret_dest] = o.ret_dest_name;
  }
  return labels;
}

function buildDestMaps(destinationsByCountry) {
  const destMap = {};
  const countryMap = {};
  for (const [country, cities] of Object.entries(destinationsByCountry || {})) {
    for (const [code, info] of Object.entries(cities)) {
      destMap[code] = { name: info.name, country };
      countryMap[code] = country;
    }
  }
  return { destMap, countryMap };
}

function destLabel(code) {
  const d = state.destMap[code];
  return d ? `${d.name}(${code})` : code;
}

function originLabel(code) {
  return state.raw?.origins?.[code] ? `${state.raw.origins[code]}(${code})` : code;
}

function cityName(code) {
  if (state.cityLabels[code]) return state.cityLabels[code];
  if (state.raw?.origins?.[code]) return state.raw.origins[code];
  const d = state.destMap[code];
  return d ? d.name : code;
}

function formatRouteLabel(o) {
  if (o.type === "round_trip") {
    return `${cityName(o.origin)} ⇄ ${cityName(o.out_dest)}`;
  }
  return `${cityName(o.origin)} → ${cityName(o.out_dest)} · ${cityName(o.ret_dest)} → ${cityName(o.ret_origin)}`;
}

function applyFilters() {
  const f = state.filters;
  return state.offers.filter((o) => {
    if (f.trip !== "all" && o.type !== f.trip) return false;
    if (f.countries.size && !f.countries.has(state.countryMap[o.out_dest])) return false;
    if (f.dests.size && !f.dests.has(o.out_dest) && !f.dests.has(o.ret_dest)) return false;
    if (f.origins.size && !f.origins.has(o.origin) && !f.origins.has(o.ret_origin)) return false;
    if (o.price < f.priceMin || o.price > f.priceMax) return false;
    if (f.bucket) {
      const b = state.priceBuckets.find((x) => x.id === f.bucket);
      if (b && (o.price < b.min || o.price > b.max)) return false;
    }
    return true;
  });
}

function applyFiltersWithoutBucket() {
  const saved = state.filters.bucket;
  state.filters.bucket = null;
  const result = applyFilters();
  state.filters.bucket = saved;
  return result;
}

function sortOffers(list) {
  const sorted = [...list];
  const [field, dir] = state.sortBy.split("-");
  const mul = dir === "asc" ? 1 : -1;
  sorted.sort((a, b) => {
    if (field === "price") return (a.price - b.price) * mul;
    if (field === "dest") return a.out_dest.localeCompare(b.out_dest) * mul;
    if (field === "date") return (a.out || "").localeCompare(b.out || "") * mul;
    if (field === "stay") return ((a.stay_days || 0) - (b.stay_days || 0)) * mul;
    return 0;
  });
  return sorted;
}

function chartDefaults() {
  if (typeof Chart === "undefined") return;
  Chart.defaults.color = "#5c5a54";
  Chart.defaults.borderColor = "rgba(13, 110, 110, 0.12)";
  Chart.defaults.font.family = "ui-monospace, monospace";
  Chart.defaults.font.size = 10;
}

function destroyChart(key) {
  if (state.charts[key]) {
    state.charts[key].destroy();
    delete state.charts[key];
  }
}

function updateDestBar(filtered) {
  if (typeof Chart === "undefined") return;
  destroyChart("destBar");
  const byDest = {};
  for (const o of filtered) {
    if (!byDest[o.out_dest] || o.price < byDest[o.out_dest]) byDest[o.out_dest] = o.price;
  }
  const entries = Object.entries(byDest).sort((a, b) => a[1] - b[1]).slice(0, 20);
  const ctx = document.getElementById("chart-dest-bar");
  if (!ctx) return;
  state.charts.destBar = new Chart(ctx, {
    type: "bar",
    data: {
      labels: entries.map(([c]) => destLabel(c)),
      datasets: [{
        label: "最低价 ¥",
        data: entries.map(([, p]) => p),
        backgroundColor: entries.map((_, i) => CHART_COLORS[i % CHART_COLORS.length] + "99"),
        borderColor: entries.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
        borderWidth: 1,
        borderRadius: 3,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: "rgba(13,110,110,0.08)" }, ticks: { callback: (v) => "¥" + v } },
        y: { grid: { display: false } },
      },
    },
  });
}

function updatePriceHist(filtered) {
  if (typeof Chart === "undefined") return;
  destroyChart("priceHist");
  const counts = state.priceBuckets.map((b) =>
    filtered.filter((o) => o.price >= b.min && o.price <= b.max).length
  );
  const ctx = document.getElementById("chart-price-hist");
  if (!ctx || !state.priceBuckets.length) return;
  state.charts.priceHist = new Chart(ctx, {
    type: "bar",
    data: {
      labels: state.priceBuckets.map((b) => b.label),
      datasets: [{
        label: "命中数",
        data: counts,
        backgroundColor: "rgba(232, 93, 59, 0.45)",
        borderColor: "#e85d3b",
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(13,110,110,0.08)" } },
        x: { grid: { display: false } },
      },
    },
  });
}

function updateCountryDonut(filtered) {
  if (typeof Chart === "undefined") return;
  destroyChart("country");
  const counts = {};
  for (const o of filtered) {
    const c = state.countryMap[o.out_dest] || "其他";
    counts[c] = (counts[c] || 0) + 1;
  }
  const labels = Object.keys(counts);
  const ctx = document.getElementById("chart-country");
  if (!ctx) return;
  state.charts.country = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: labels.map((l) => counts[l]),
        backgroundColor: labels.map((_, i) => CHART_COLORS[i % CHART_COLORS.length] + "cc"),
        borderColor: "#fffdf8",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: {
          position: "right",
          labels: { boxWidth: 10, padding: 8, font: { size: 9 } },
        },
      },
    },
  });
}

function updateScatter(filtered) {
  if (typeof Chart === "undefined") return;
  destroyChart("scatter");
  const groups = {};
  for (const o of filtered) {
    const key = `${o.stay_days}|${o.price}|${o.out_dest}`;
    if (!groups[key]) groups[key] = { x: o.stay_days, y: o.price, dest: o.out_dest, count: 0 };
    groups[key].count++;
  }
  const points = Object.values(groups);
  const dests = [...new Set(points.map((p) => p.dest))];
  const datasets = dests.slice(0, 12).map((dest, i) => ({
    label: destLabel(dest),
    data: points.filter((p) => p.dest === dest).map((p) => ({ x: p.x, y: p.y, r: 4 + p.count * 2 })),
    backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + "88",
    borderColor: CHART_COLORS[i % CHART_COLORS.length],
  }));
  const ctx = document.getElementById("chart-scatter");
  if (!ctx) return;
  state.charts.scatter = new Chart(ctx, {
    type: "bubble",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: dests.length <= 8, labels: { boxWidth: 8, font: { size: 8 } } } },
      scales: {
        x: { title: { display: true, text: "停留天数" }, grid: { color: "rgba(13,110,110,0.08)" } },
        y: { title: { display: true, text: "价格 ¥" }, grid: { color: "rgba(13,110,110,0.08)" } },
      },
    },
  });
}

function updateDateChart(filtered) {
  if (typeof Chart === "undefined") return;
  destroyChart("date");
  const counts = {};
  for (const o of filtered) {
    if (o.out) counts[o.out] = (counts[o.out] || 0) + 1;
  }
  const dates = Object.keys(counts).sort();
  const ctx = document.getElementById("chart-date");
  if (!ctx) return;
  state.charts.date = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates.map((d) => d.slice(5)),
      datasets: [{
        label: "命中数",
        data: dates.map((d) => counts[d]),
        borderColor: "#0d6e6e",
        backgroundColor: "rgba(13, 110, 110, 0.12)",
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#0d6e6e",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(13,110,110,0.08)" } },
        x: { grid: { display: false } },
      },
    },
  });
}

function updateCharts(filtered) {
  updateDestBar(filtered);
  updatePriceHist(filtered);
  updateCountryDonut(filtered);
  updateScatter(filtered);
  updateDateChart(filtered);
}

function updatePager(total, pages) {
  const pager = document.getElementById("pager");
  if (!pager) return;
  let page = state.page;
  if (page > pages) page = pages;
  if (page < 1) page = 1;
  state.page = page;

  const start = total ? (page - 1) * state.pageSize : 0;
  const end = Math.min(start + state.pageSize, total);
  pager.querySelector(".pg-info").textContent = total
    ? `第 ${page} / ${pages} 页 · ${start + 1}–${end} / 共 ${total} 条`
    : "共 0 条";
  pager.querySelector(".pg-prev").disabled = page <= 1;
  pager.querySelector(".pg-next").disabled = page >= pages;
  const jumpInput = pager.querySelector(".pg-jump");
  if (jumpInput) {
    jumpInput.max = pages;
    jumpInput.placeholder = String(page);
  }
}

function formatOutRoute(o) {
  return `${cityName(o.origin)} → ${cityName(o.out_dest)}`;
}

function formatRetRoute(o) {
  return `${cityName(o.ret_dest)} → ${cityName(o.ret_origin)}`;
}

function legDetailOut(o) {
  if (o.summary_out) return o.summary_out;
  if (!o.detail) return "—";
  const part = o.detail.split(" · ")[0] || o.detail;
  return part.replace(/^去:\s*/, "").replace(/^去\s*¥[\d.]+\s*:\s*/, "");
}

function legDetailRet(o) {
  if (o.summary_ret) return o.summary_ret;
  if (!o.detail) return "—";
  const parts = o.detail.split(" · ");
  const part = parts.length > 1 ? parts[parts.length - 1] : parts[0];
  return part.replace(/^回:\s*/, "").replace(/^回\s*¥[\d.]+\s*:\s*/, "");
}

function buildOutLegs(offers) {
  const map = new Map();
  for (const o of offers) {
    const legPrice = o.price_out != null ? o.price_out : o.type === "round_trip" ? o.price : null;
    if (legPrice == null) continue;
    const detail = legDetailOut(o);
    const key = `${o.origin}|${o.out_dest}|${o.out}|${detail}`;
    const row = {
      price: legPrice,
      route: formatOutRoute(o),
      date: o.out,
      detail,
      type: o.type,
      isRoundTotal: o.type === "round_trip",
    };
    const prev = map.get(key);
    if (!prev || row.price < prev.price) map.set(key, row);
  }
  return [...map.values()].sort((a, b) => a.price - b.price);
}

function buildRetLegs(offers) {
  const map = new Map();
  for (const o of offers) {
    const legPrice = o.price_ret != null ? o.price_ret : o.type === "round_trip" ? o.price : null;
    if (legPrice == null) continue;
    const detail = legDetailRet(o);
    const key = `${o.ret_dest}|${o.ret_origin}|${o.ret}|${detail}`;
    const row = {
      price: legPrice,
      route: formatRetRoute(o),
      date: o.ret,
      detail,
      type: o.type,
      isRoundTotal: o.type === "round_trip",
    };
    const prev = map.get(key);
    if (!prev || row.price < prev.price) map.set(key, row);
  }
  return [...map.values()].sort((a, b) => a.price - b.price);
}

function renderLegTable(tbodyId, countId, rows) {
  const tbody = document.getElementById(tbodyId);
  const countEl = document.getElementById(countId);
  if (!tbody || !countEl) return;

  countEl.textContent = rows.length ? `共 ${rows.length} 条` : "0 条";

  if (!rows.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">无匹配结果</td></tr>';
    return;
  }

  tbody.innerHTML = rows
    .map((row, i) => {
      const typeCls = row.type === "round_trip" ? "rt" : "oj";
      const typeText = row.type === "round_trip" ? "往返" : "开口";
      const priceCls = row.isRoundTotal ? "price-cell price-cell--leg rt-total" : "price-cell price-cell--leg";
      const priceNote = row.isRoundTotal ? `<div class="leg-price-note">联票总价</div>` : "";
      return `<tr>
      <td>${i + 1}</td>
      <td class="route-cell">${esc(row.route)}</td>
      <td>${esc(row.date || "")}</td>
      <td class="${priceCls}">¥${row.price.toFixed(0)}${priceNote}</td>
      <td><span class="type-badge ${typeCls}">${typeText}</span></td>
      <td class="detail-cell">${esc(row.detail)}</td>
    </tr>`;
    })
    .join("");
}

function updateLegTables(filtered) {
  renderLegTable("out-legs-tbody", "out-leg-count", buildOutLegs(filtered));
  renderLegTable("ret-legs-tbody", "ret-leg-count", buildRetLegs(filtered));
}

function updateTable(sorted) {
  const tbody = document.getElementById("offers-tbody");
  const total = sorted.length;
  const pages = Math.max(1, Math.ceil(total / state.pageSize));
  updatePager(total, pages);

  document.getElementById("table-count").textContent =
    total ? `筛选后 ${total} 条` : "0 条";

  if (!total) {
    tbody.innerHTML =
      '<tr class="empty-row"><td colspan="9">无匹配结果，请调整筛选条件</td></tr>';
    return;
  }

  const start = (state.page - 1) * state.pageSize;
  const slice = sorted.slice(start, start + state.pageSize);

  tbody.innerHTML = slice
    .map((o, i) => {
      const typeCls = o.type === "round_trip" ? "rt" : "oj";
      const typeText = o.type === "round_trip" ? "往返" : "开口程";
      const bookableCls = o.bookable ? "bookable-yes" : "bookable-no";
      const bookableText = o.bookable ? "可订" : "分段价";
      const detail = o.detail ? esc(o.detail) : "—";
      return `<tr>
      <td>${start + i + 1}</td>
      <td><span class="type-badge ${typeCls}">${typeText}</span></td>
      <td class="route-cell">${esc(formatRouteLabel(o))}</td>
      <td>${esc(o.out || "")}</td>
      <td>${esc(o.ret || "-")}</td>
      <td>${esc(o.stay_days != null ? o.stay_days + "天" : "-")}</td>
      <td class="price-cell">¥${o.price.toFixed(0)}</td>
      <td class="${bookableCls}">${bookableText}</td>
      <td class="detail-cell">${detail}</td>
    </tr>`;
    })
    .join("");
}

function render(resetPage) {
  if (resetPage) state.page = 1;
  const filtered = applyFilters();
  const sorted = sortOffers(filtered);
  updateCharts(filtered);
  updateLegTables(filtered);
  updateTable(sorted);
}

function jumpToPage() {
  const pager = document.getElementById("pager");
  const sorted = sortOffers(applyFilters());
  const pages = Math.max(1, Math.ceil(sorted.length / state.pageSize));
  const raw = parseInt(pager.querySelector(".pg-jump").value, 10);
  if (!Number.isFinite(raw)) return;
  state.page = Math.max(1, Math.min(pages, raw));
  updateTable(sorted);
}

function renderHeroStats() {
  const all = state.offers;
  const meta = state.raw.meta || {};
  const dr = meta.date_range || ["", ""];
  const mode = meta.search_mode ? ` · 模式 ${meta.search_mode}` : "";
  const gen = meta.generated_at ? ` · ${meta.generated_at}` : "";

  const summary = meta.query_summary ? `${meta.query_summary} · ` : "";
  const stayLine =
    meta.max_stay_days != null
      ? `停留 ${meta.min_stay_days ?? "—"}~${meta.max_stay_days} 天`
      : `最少停留 ${meta.min_stay_days ?? "—"} 天`;
  document.getElementById("meta-line").textContent =
    `${summary}日期窗 ${dr[0]} ~ ${dr[1]} · 限价 ¥${meta.max_price ?? "—"} · ${stayLine}${mode}${gen}`;

  if (!all.length) {
    const abnormal = meta.pricing_service_abnormal;
    const warn = meta.pricing_service_message || "查价服务异常";
    document.getElementById("hero-stats").innerHTML = abnormal
      ? `<div class="stat-pill stat-pill-warn"><div class="label">查价状态</div><div class="value">${esc(warn)}</div></div>`
      : '<div class="stat-pill"><div class="label">总命中</div><div class="value">0</div></div>';
    return;
  }

  const prices = all.map((o) => o.price);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const rt = all.filter((o) => o.type === "round_trip").length;
  const oj = all.filter((o) => o.type === "open_jaw").length;

  document.getElementById("hero-stats").innerHTML = [
    { label: "总命中", value: all.length },
    { label: "往返", value: rt },
    { label: "开口程", value: oj, cls: "coral" },
    { label: "最低价", value: `¥${minP.toFixed(0)}`, cls: "coral" },
    { label: "最高价", value: `¥${maxP.toFixed(0)}` },
  ]
    .map(
      (s) => `
    <div class="stat-pill">
      <div class="label">${s.label}</div>
      <div class="value ${s.cls || ""}">${s.value}</div>
    </div>`
    )
    .join("");
}

function buildChips(containerId, items, labelFn) {
  const el = document.getElementById(containerId);
  el.innerHTML = items
    .map((item) => {
      const val = typeof item === "string" ? item : item;
      const label = labelFn ? labelFn(item) : val;
      return `<button type="button" class="chip" data-key="${containerId}" data-val="${val}">${esc(label)}</button>`;
    })
    .join("");
}

function setupFilters() {
  const countries = Object.keys(state.raw.destinations_by_country || {});
  const countryGroup = document.getElementById("country-chips")?.closest(".filter-group");
  if (countryGroup) {
    countryGroup.style.display = countries.length > 1 ? "" : "none";
  }
  buildChips("country-chips", countries);

  const dests = Object.keys(state.destMap).sort((a, b) =>
    (state.destMap[a]?.name || a).localeCompare(state.destMap[b]?.name || b, "zh")
  );
  buildChips("dest-chips", dests, (code) => destLabel(code));

  const origins = Object.keys(state.raw.origins || {});
  buildChips("origin-chips", origins, (code) => originLabel(code));

  if (!state.offers.length) return;

  syncPriceBuckets();

  const prices = state.offers.map((o) => o.price);
  const pMin = Math.floor(Math.min(...prices) / 50) * 50;
  const pMax = Math.ceil(Math.max(...prices) / 50) * 50;
  state.filters.priceMin = pMin;
  state.filters.priceMax = pMax;

  const minSlider = document.getElementById("price-min");
  const maxSlider = document.getElementById("price-max");
  minSlider.min = maxSlider.min = pMin;
  minSlider.max = maxSlider.max = pMax;
  minSlider.step = maxSlider.step = Math.max(50, roundPriceStep(pMax - pMin) / 5);
  minSlider.value = pMin;
  maxSlider.value = pMax;

  renderPriceLabel();
  renderPriceBuckets();
}

function renderPriceLabel() {
  const f = state.filters;
  document.getElementById("price-range-label").textContent = `¥${f.priceMin} – ¥${f.priceMax}`;
}

function renderPriceBuckets() {
  const el = document.getElementById("price-buckets");
  if (!state.priceBuckets.length) {
    el.innerHTML = "";
    return;
  }
  const filtered = applyFiltersWithoutBucket();
  el.innerHTML = state.priceBuckets.map((b) => {
    const count = filtered.filter((o) => o.price >= b.min && o.price <= b.max).length;
    const active = state.filters.bucket === b.id ? "active" : "";
    return `<button type="button" class="bucket ${active}" data-bucket="${b.id}">
      <div class="range-text">${b.label}</div>
      <div class="count-text">${count}</div>
    </button>`;
  }).join("");
}

function toggleSet(set, val, chip) {
  if (set.has(val)) {
    set.delete(val);
    chip.classList.remove("active");
  } else {
    set.add(val);
    chip.classList.add("active");
  }
}

function bindEvents() {
  document.getElementById("trip-tabs").addEventListener("click", (e) => {
    const tab = e.target.closest(".tab");
    if (!tab) return;
    document.querySelectorAll(".trip-tabs .tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    state.filters.trip = tab.dataset.trip;
    render(true);
    renderPriceBuckets();
  });

  document.querySelector(".filters-panel").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) {
      const key = chip.dataset.key;
      const val = chip.dataset.val;
      if (key === "country-chips") toggleSet(state.filters.countries, val, chip);
      else if (key === "dest-chips") toggleSet(state.filters.dests, val, chip);
      else if (key === "origin-chips") toggleSet(state.filters.origins, val, chip);
      render(true);
      renderPriceBuckets();
      return;
    }

    const bucket = e.target.closest(".bucket");
    if (bucket) {
      const id = bucket.dataset.bucket;
      state.filters.bucket = state.filters.bucket === id ? null : id;
      render(true);
      renderPriceBuckets();
    }
  });

  const minSlider = document.getElementById("price-min");
  const maxSlider = document.getElementById("price-max");

  function onRangeChange() {
    let lo = Number(minSlider.value);
    let hi = Number(maxSlider.value);
    if (lo > hi) [lo, hi] = [hi, lo];
    state.filters.priceMin = lo;
    state.filters.priceMax = hi;
    state.filters.bucket = null;
    minSlider.value = lo;
    maxSlider.value = hi;
    renderPriceLabel();
    render(true);
    renderPriceBuckets();
  }

  minSlider.addEventListener("input", onRangeChange);
  maxSlider.addEventListener("input", onRangeChange);

  document.getElementById("sort-by").addEventListener("change", (e) => {
    state.sortBy = e.target.value;
    render(true);
  });

  document.getElementById("reset-filters").addEventListener("click", () => {
    state.filters.trip = "all";
    state.filters.countries.clear();
    state.filters.dests.clear();
    state.filters.origins.clear();
    state.filters.bucket = null;
    if (state.offers.length) {
      const prices = state.offers.map((o) => o.price);
      state.filters.priceMin = Math.floor(Math.min(...prices) / 50) * 50;
      state.filters.priceMax = Math.ceil(Math.max(...prices) / 50) * 50;
      minSlider.value = state.filters.priceMin;
      maxSlider.value = state.filters.priceMax;
    }
    document.querySelectorAll(".chip.active").forEach((c) => c.classList.remove("active"));
    document.querySelectorAll(".trip-tabs .tab").forEach((t) =>
      t.classList.toggle("active", t.dataset.trip === "all")
    );
    renderPriceLabel();
    render(true);
    renderPriceBuckets();
  });

  const pager = document.getElementById("pager");
  pager.querySelector(".pg-prev").onclick = () => {
    state.page -= 1;
    render(false);
  };
  pager.querySelector(".pg-next").onclick = () => {
    state.page += 1;
    render(false);
  };
  pager.querySelector(".pg-size").onchange = (e) => {
    state.pageSize = parseInt(e.target.value, 10);
    render(true);
  };
  pager.querySelector(".pg-go").onclick = jumpToPage;
  pager.querySelector(".pg-jump").addEventListener("keydown", (e) => {
    if (e.key === "Enter") jumpToPage();
  });
}

let reportEventsBound = false;

function initReport(raw) {
  chartDefaults();
  state.raw = raw;
  state.filters.trip = "all";
  state.filters.countries.clear();
  state.filters.dests.clear();
  state.filters.origins.clear();
  state.filters.bucket = null;
  state.sortBy = "price-asc";
  state.page = 1;
  Object.keys(state.charts).forEach((k) => destroyChart(k));
  state.charts = {};

  const maps = buildDestMaps(state.raw.destinations_by_country);
  state.destMap = maps.destMap;
  state.countryMap = maps.countryMap;
  state.offers = state.raw.offers || [];
  state.cityLabels = buildCityLabelsFromOffers(state.offers);
  for (const [code, name] of Object.entries(state.raw.origins || {})) {
    state.cityLabels[code] = name;
  }

  renderHeroStats();
  setupFilters();
  if (!reportEventsBound) {
    bindEvents();
    reportEventsBound = true;
  }
  render(true);
}

window.ReportApp = {
  init(raw) {
    try {
      initReport(raw);
    } catch (err) {
      const meta = document.getElementById("meta-line");
      if (meta) meta.textContent = "报告加载失败：" + err.message;
      console.error(err);
    }
  },
};
