/* 穷举特价可视化 — 数据加载、筛选、图表 */

const PRICE_BUCKETS = [
  { id: "b1", label: "< ¥2100", min: 0, max: 2099 },
  { id: "b2", label: "¥2100–2200", min: 2100, max: 2199 },
  { id: "b3", label: "¥2200–2300", min: 2200, max: 2299 },
  { id: "b4", label: "¥2300–2400", min: 2300, max: 2399 },
  { id: "b5", label: "≥ ¥2400", min: 2400, max: Infinity },
];

const CHART_COLORS = [
  "#00d4aa", "#f5a623", "#ff6b8a", "#5b8def", "#c084fc",
  "#34d399", "#fb923c", "#f472b6", "#38bdf8", "#a3e635",
];

const state = {
  raw: null,
  offers: [],
  destMap: {},
  countryMap: {},
  filters: {
    trip: "all",
    countries: new Set(),
    dests: new Set(),
    origins: new Set(),
    priceMin: 0,
    priceMax: 3000,
    bucket: null,
  },
  sortBy: "price-asc",
  charts: {},
};

function normalizeOffer(o, idx) {
  if (o.type === "round_trip") {
    return {
      id: idx,
      type: "round_trip",
      origin: o.origin,
      out_dest: o.dest,
      ret_dest: o.dest,
      ret_origin: o.origin,
      out: o.out,
      ret: o.ret,
      stay_days: o.stay_days,
      price: o.price,
      detail: o.detail,
    };
  }
  return {
    id: idx,
    type: "open_jaw",
    origin: o.origin,
    out_dest: o.out_dest,
    ret_dest: o.ret_dest,
    ret_origin: o.ret_origin,
    out: o.out,
    ret: o.ret,
    stay_days: o.stay_days,
    price: o.price,
    detail: null,
  };
}

function buildDestMaps(destinationsByCountry) {
  const destMap = {};
  const countryMap = {};
  for (const [country, cities] of Object.entries(destinationsByCountry)) {
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
      const b = PRICE_BUCKETS.find((x) => x.id === f.bucket);
      if (b && (o.price < b.min || o.price > b.max)) return false;
    }
    return true;
  });
}

function sortOffers(list) {
  const sorted = [...list];
  const [field, dir] = state.sortBy.split("-");
  const mul = dir === "asc" ? 1 : -1;
  sorted.sort((a, b) => {
    if (field === "price") return (a.price - b.price) * mul;
    if (field === "dest") return a.out_dest.localeCompare(b.out_dest) * mul;
    if (field === "date") return a.out.localeCompare(b.out) * mul;
    if (field === "stay") return (a.stay_days - b.stay_days) * mul;
    return 0;
  });
  return sorted;
}

function chartDefaults() {
  Chart.defaults.color = "#5a6a7a";
  Chart.defaults.borderColor = "rgba(0, 212, 170, 0.1)";
  Chart.defaults.font.family = "'DM Mono', monospace";
  Chart.defaults.font.size = 10;
}

function destroyChart(key) {
  if (state.charts[key]) {
    state.charts[key].destroy();
    delete state.charts[key];
  }
}

function updateDestBar(filtered) {
  destroyChart("destBar");
  const byDest = {};
  for (const o of filtered) {
    const key = o.out_dest;
    if (!byDest[key] || o.price < byDest[key]) byDest[key] = o.price;
  }
  const entries = Object.entries(byDest).sort((a, b) => a[1] - b[1]).slice(0, 20);
  const ctx = document.getElementById("chart-dest-bar");
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
        x: { grid: { color: "rgba(0,212,170,0.06)" }, ticks: { callback: (v) => "¥" + v } },
        y: { grid: { display: false } },
      },
    },
  });
}

function updatePriceHist(filtered) {
  destroyChart("priceHist");
  const counts = PRICE_BUCKETS.map((b) =>
    filtered.filter((o) => o.price >= b.min && o.price <= b.max).length
  );
  const ctx = document.getElementById("chart-price-hist");
  state.charts.priceHist = new Chart(ctx, {
    type: "bar",
    data: {
      labels: PRICE_BUCKETS.map((b) => b.label),
      datasets: [{
        label: "命中数",
        data: counts,
        backgroundColor: "rgba(245, 166, 35, 0.55)",
        borderColor: "#f5a623",
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(0,212,170,0.06)" } },
        x: { grid: { display: false } },
      },
    },
  });
}

function updateCountryDonut(filtered) {
  destroyChart("country");
  const counts = {};
  for (const o of filtered) {
    const c = state.countryMap[o.out_dest] || "其他";
    counts[c] = (counts[c] || 0) + 1;
  }
  const labels = Object.keys(counts);
  const ctx = document.getElementById("chart-country");
  state.charts.country = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: labels.map((l) => counts[l]),
        backgroundColor: labels.map((_, i) => CHART_COLORS[i % CHART_COLORS.length] + "cc"),
        borderColor: "#151d28",
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
  destroyChart("scatter");
  const groups = {};
  for (const o of filtered) {
    const key = `${o.stay_days}|${o.price}|${o.out_dest}`;
    if (!groups[key]) groups[key] = { x: o.stay_days, y: o.price, dest: o.out_dest, count: 0 };
    groups[key].count++;
  }
  const points = Object.values(groups);
  const dests = [...new Set(points.map((p) => p.dest))];
  const datasets = dests.map((dest, i) => ({
    label: destLabel(dest),
    data: points.filter((p) => p.dest === dest).map((p) => ({ x: p.x, y: p.y, r: 4 + p.count * 2 })),
    backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + "88",
    borderColor: CHART_COLORS[i % CHART_COLORS.length],
  }));
  const ctx = document.getElementById("chart-scatter");
  state.charts.scatter = new Chart(ctx, {
    type: "bubble",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: dests.length <= 8, labels: { boxWidth: 8, font: { size: 8 } } } },
      scales: {
        x: { title: { display: true, text: "停留天数" }, grid: { color: "rgba(0,212,170,0.06)" } },
        y: { title: { display: true, text: "价格 ¥" }, grid: { color: "rgba(0,212,170,0.06)" } },
      },
    },
  });
}

function updateDateChart(filtered) {
  destroyChart("date");
  const counts = {};
  for (const o of filtered) counts[o.out] = (counts[o.out] || 0) + 1;
  const dates = Object.keys(counts).sort();
  const ctx = document.getElementById("chart-date");
  state.charts.date = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates.map((d) => d.slice(5)),
      datasets: [{
        label: "命中数",
        data: dates.map((d) => counts[d]),
        borderColor: "#00d4aa",
        backgroundColor: "rgba(0, 212, 170, 0.12)",
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#00d4aa",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(0,212,170,0.06)" } },
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

function updateTable(filtered) {
  const sorted = sortOffers(filtered);
  const tbody = document.getElementById("offers-tbody");
  document.getElementById("table-count").textContent = `${sorted.length} 条`;

  if (!sorted.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="8">无匹配结果，请调整筛选条件</td></tr>';
    return;
  }

  tbody.innerHTML = sorted.map((o, i) => {
    const typeCls = o.type === "round_trip" ? "rt" : "oj";
    const typeText = o.type === "round_trip" ? "往返" : "开口程";
    const detail = o.detail
      ? `<div>${o.detail.out || ""}</div><div>${o.detail.ret || ""}</div>`
      : "—";
    return `<tr>
      <td>${i + 1}</td>
      <td><span class="type-badge ${typeCls}">${typeText}</span></td>
      <td class="route-cell">${formatRouteLabel(o)}</td>
      <td>${o.out}</td>
      <td>${o.ret}</td>
      <td>${o.stay_days}天</td>
      <td class="price-cell">¥${o.price.toFixed(0)}</td>
      <td class="detail-cell">${detail}</td>
    </tr>`;
  }).join("");
}

function render() {
  const filtered = applyFilters();
  updateCharts(filtered);
  updateTable(filtered);
}

function renderHeroStats() {
  const all = state.offers;
  const prices = all.map((o) => o.price);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const rt = all.filter((o) => o.type === "round_trip").length;
  const oj = all.filter((o) => o.type === "open_jaw").length;

  document.getElementById("meta-line").textContent =
    `${state.raw.date_range[0]} → ${state.raw.date_range[1]} · 限价 ¥${state.raw.max_price} · 最少停留 ${state.raw.min_stay_days} 天 · 查询 ${(state.raw.rt_queries || 0) + (state.raw.ow_queries || 0)} 次`;

  document.getElementById("hero-stats").innerHTML = [
    { label: "总命中", value: all.length },
    { label: "往返", value: rt, cls: "" },
    { label: "开口程", value: oj, cls: "amber" },
    { label: "最低价", value: `¥${minP.toFixed(0)}`, cls: "amber" },
    { label: "最高价", value: `¥${maxP.toFixed(0)}` },
  ].map((s) => `
    <div class="stat-pill">
      <div class="label">${s.label}</div>
      <div class="value ${s.cls || ""}">${s.value}</div>
    </div>
  `).join("");
}

function buildChips(containerId, items, key, labelFn) {
  const el = document.getElementById(containerId);
  el.innerHTML = items.map((item) => {
    const val = typeof item === "string" ? item : item[key];
    const label = labelFn ? labelFn(item) : val;
    return `<button type="button" class="chip" data-key="${containerId}" data-val="${val}">${label}</button>`;
  }).join("");
}

function setupFilters() {
  const countries = Object.keys(state.raw.destinations_by_country);
  buildChips("country-chips", countries, null, null);

  const dests = Object.keys(state.destMap).sort((a, b) =>
    state.destMap[a].name.localeCompare(state.destMap[b].name, "zh")
  );
  buildChips("dest-chips", dests, null, (code) => destLabel(code));

  const origins = Object.keys(state.raw.origins);
  buildChips("origin-chips", origins, null, (code) => originLabel(code));

  const prices = state.offers.map((o) => o.price);
  const pMin = Math.floor(Math.min(...prices) / 50) * 50;
  const pMax = Math.ceil(Math.max(...prices) / 50) * 50;
  state.filters.priceMin = pMin;
  state.filters.priceMax = pMax;

  const minSlider = document.getElementById("price-min");
  const maxSlider = document.getElementById("price-max");
  minSlider.min = maxSlider.min = pMin;
  minSlider.max = maxSlider.max = pMax;
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
  const filtered = applyFiltersWithoutBucket();
  el.innerHTML = PRICE_BUCKETS.map((b) => {
    const count = filtered.filter((o) => o.price >= b.min && o.price <= b.max).length;
    const active = state.filters.bucket === b.id ? "active" : "";
    return `<button type="button" class="bucket ${active}" data-bucket="${b.id}">
      <div class="range-text">${b.label}</div>
      <div class="count-text">${count}</div>
    </button>`;
  }).join("");
}

function applyFiltersWithoutBucket() {
  const saved = state.filters.bucket;
  state.filters.bucket = null;
  const result = applyFilters();
  state.filters.bucket = saved;
  return result;
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
    render();
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
      render();
      renderPriceBuckets();
      return;
    }

    const bucket = e.target.closest(".bucket");
    if (bucket) {
      const id = bucket.dataset.bucket;
      state.filters.bucket = state.filters.bucket === id ? null : id;
      render();
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
    render();
    renderPriceBuckets();
  }

  minSlider.addEventListener("input", onRangeChange);
  maxSlider.addEventListener("input", onRangeChange);

  document.getElementById("sort-by").addEventListener("change", (e) => {
    state.sortBy = e.target.value;
    updateTable(applyFilters());
  });

  document.getElementById("reset-filters").addEventListener("click", () => {
    state.filters.trip = "all";
    state.filters.countries.clear();
    state.filters.dests.clear();
    state.filters.origins.clear();
    state.filters.bucket = null;
    const prices = state.offers.map((o) => o.price);
    state.filters.priceMin = Math.floor(Math.min(...prices) / 50) * 50;
    state.filters.priceMax = Math.ceil(Math.max(...prices) / 50) * 50;
    document.querySelectorAll(".chip.active").forEach((c) => c.classList.remove("active"));
    document.querySelectorAll(".trip-tabs .tab").forEach((t) => t.classList.toggle("active", t.dataset.trip === "all"));
    minSlider.value = state.filters.priceMin;
    maxSlider.value = state.filters.priceMax;
    renderPriceLabel();
    render();
    renderPriceBuckets();
  });
}

async function loadVizData() {
  const params = new URLSearchParams(location.search);
  const searchId = params.get("search_id");
  if (searchId) {
    const apiBase = (() => {
      const m = location.pathname.match(/^(.*\/viz)\/?/);
      const prefix = m ? m[1].replace(/\/viz$/, "") : "";
      return `${prefix}/nl-search`;
    })();
    const res = await fetch(`${apiBase}/api/search/${encodeURIComponent(searchId)}/viz-bundle`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "无法加载在线查价结果，请返回 nl-search 重新搜索");
    }
    return res.json();
  }
  const res = await fetch("data.json");
  if (!res.ok) throw new Error("无法加载 data.json，请通过本地服务器访问，或使用 ?search_id= 联动在线查价");
  return res.json();
}

async function init() {
  chartDefaults();
  state.raw = await loadVizData();

  const maps = buildDestMaps(state.raw.destinations_by_country || {});
  state.destMap = maps.destMap;
  state.countryMap = maps.countryMap;

  let idx = 0;
  state.offers = [
    ...(state.raw.rt_hits || []).map((o) => normalizeOffer(o, idx++)),
    ...(state.raw.oj_hits || []).map((o) => normalizeOffer(o, idx++)),
  ];

  const metaEl = document.getElementById("meta-line");
  const hintEl = document.getElementById("viz-source-hint");
  if (state.raw.meta?.source === "nl-search") {
    metaEl.textContent = `在线查价联动 · ${state.offers.length} 条命中`;
    if (hintEl) hintEl.textContent = "本次查价结果（实时）";
  } else if (hintEl) {
    hintEl.textContent = "静态穷举快照 data.json";
  }

  renderHeroStats();
  setupFilters();
  bindEvents();
  render();
}

init().catch((err) => {
  document.getElementById("meta-line").textContent = err.message;
  console.error(err);
});
