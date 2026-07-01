/* 价格矩阵结果可视化 */
(function() {
        let tooltipEl = null;

        function ensureTooltip() {
            if (tooltipEl) return tooltipEl;
            tooltipEl = document.createElement("div");
            tooltipEl.className = "matrix-tooltip";
            tooltipEl.id = "matrix-tooltip";
            document.body.appendChild(tooltipEl);
            return tooltipEl;
        }

        function hideTooltip() {
            const el = document.getElementById("matrix-tooltip");
            if (el) el.style.display = "none";
        }

        function showTooltip(e, lines) {
            const el = ensureTooltip();
            el.textContent = lines.join("\n");
            el.style.display = "block";
            const pad = 12;
            let x = e.clientX + pad;
            let y = e.clientY + pad;
            const rect = el.getBoundingClientRect();
            if (x + rect.width > window.innerWidth - 8) x = e.clientX - rect.width - pad;
            if (y + rect.height > window.innerHeight - 8) y = e.clientY - rect.height - pad;
            el.style.left = `${x}px`;
            el.style.top = `${y}px`;
        }

        function formatShortDate(iso) {
            if (!iso) return "";
            const parts = iso.split("-");
            return parts.length >= 3 ? `${parts[1]}-${parts[2]}` : iso;
        }

        function routeKey(origin, dest) {
            return `${origin}|${dest}`;
        }

        function groupOffersByRoute(offers) {
            const map = new Map();
            (offers || []).forEach((o) => {
                const dest = o.out_dest || o.dest;
                const key = routeKey(o.origin, dest);
                if (!map.has(key)) map.set(key, []);
                map.get(key).push(o);
            });
            return map;
        }

        function pairKey(out, ret) {
            return `${out}|${ret}`;
        }

        function buildPairMap(offers) {
            const m = {};
            (offers || []).forEach((o) => {
                const k = pairKey(o.out_date, o.ret_date || "");
                if (!m[k] || o.price < m[k].price) m[k] = o;
            });
            return m;
        }

        function computeGlobalScale(offers) {
            const prices = (offers || []).map((o) => o.price).filter((p) => typeof p === "number");
            if (!prices.length) return { min: 0, max: 0 };
            return { min: Math.min(...prices), max: Math.max(...prices) };
        }

        function colorForPrice(price, minP, maxP) {
            if (maxP <= minP) return "hsl(130, 48%, 88%)";
            const t = Math.max(0, Math.min(1, (price - minP) / (maxP - minP)));
            const h = 130 - t * 130;
            const s = 48 + t * 14;
            const l = 88 - t * 16;
            return `hsl(${h}, ${s}%, ${l}%)`;
        }

        function routeLabel(route) {
            return `${route.origin_name || route.origin} → ${route.dest_name || route.dest}`;
        }

        function buildRouteSummaries(routes, byRoute, globalScale) {
            return routes.map((route) => {
                const key = routeKey(route.origin, route.dest);
                const offers = byRoute.get(key) || [];
                if (!offers.length) {
                    return {
                        route,
                        label: routeLabel(route),
                        minPrice: null,
                        maxPrice: null,
                        minOffer: null,
                    };
                }
                let minO = offers[0];
                let maxO = offers[0];
                offers.forEach((o) => {
                    if (o.price < minO.price) minO = o;
                    if (o.price > maxO.price) maxO = o;
                });
                return {
                    route,
                    label: routeLabel(route),
                    minPrice: minO.price,
                    maxPrice: maxO.price,
                    minOffer: minO,
                };
            });
        }

        function renderSummaryTable(title, rows, kind) {
            const sorted =
                kind === "min" ? [...rows].filter((r) => r.minPrice != null).sort((a, b) => a.minPrice - b.minPrice) : [...rows].filter((r) => r.maxPrice != null).sort((a, b) => b.maxPrice - a.maxPrice);

            const body = sorted.length ?
                sorted
                .map((r) => {
                        const price = kind === "min" ? r.minPrice : r.maxPrice;
                        const dateCell =
                            kind === "min" && r.minOffer ?
                            `${formatShortDate(r.minOffer.out_date)} / ${formatShortDate(r.minOffer.ret_date)}` :
                            "—";
                        return `<tr>
              <td>${r.label}</td>
              <td>¥${Math.round(price).toLocaleString()}</td>
              ${kind === "min" ? `<td>${dateCell}</td>` : ""}
            </tr>`;
          })
          .join("")
      : `<tr><td colspan="${kind === "min" ? 3 : 2}">暂无数据</td></tr>`;

    const head =
      kind === "min"
        ? "<tr><th>路线</th><th>最低价</th><th>最低价日期</th></tr>"
        : "<tr><th>路线</th><th>最高价</th></tr>";

    return `
      <div>
        <h3 style="font-size:0.9rem;color:var(--teal);margin-bottom:8px">${title}</h3>
        <table class="matrix-summary-table">${head}${body}</table>
      </div>`;
  }

  function renderMatrixCard(route, offers, outDays, retDays, globalScale) {
    const pairMap = buildPairMap(offers);
    let bestOffer = null;
    offers.forEach((o) => {
      if (!bestOffer || o.price < bestOffer.price) bestOffer = o;
    });

    const headerBest = bestOffer
      ? `最佳 ¥${Math.round(bestOffer.price).toLocaleString()} | ${formatShortDate(bestOffer.out_date)} / ${formatShortDate(bestOffer.ret_date)}`
      : "暂无命中";

    let table = `<table class="matrix-grid-table"><thead><tr><th></th>`;
    retDays.forEach((d) => {
      table += `<th>${formatShortDate(d)}</th>`;
    });
    table += "</tr></thead><tbody>";

    outDays.forEach((outD) => {
      table += `<tr><th>${formatShortDate(outD)}</th>`;
      retDays.forEach((retD) => {
        const pk = pairKey(outD, retD);
        const offer = pairMap[pk];
        if (!offer) {
          table += `<td class="matrix-cell is-empty">—</td>`;
          return;
        }
        const isBest = bestOffer && offer.id === bestOffer.id;
        const bg = colorForPrice(offer.price, globalScale.min, globalScale.max);
        const cls = `matrix-cell${isBest ? " is-best" : ""}`;
        const priceText = Math.round(offer.price).toLocaleString();
        table += `<td class="${cls}" style="background:${bg}" data-offer-id="${offer.id}">${priceText}</td>`;
      });
      table += "</tr>";
    });
    table += "</tbody></table>";

    return `
      <article class="matrix-card" data-route="${routeKey(route.origin, route.dest)}">
        <div class="matrix-card-head">
          ${routeLabel(route)}
          <div class="matrix-card-best">${headerBest}</div>
        </div>
        <div class="matrix-scroll">${table}</div>
      </article>`;
  }

  function bindCellTooltips(root, offers) {
    const byId = {};
    (offers || []).forEach((o) => {
      byId[o.id] = o;
    });
    root.querySelectorAll(".matrix-cell[data-offer-id]").forEach((cell) => {
      const offer = byId[cell.dataset.offerId];
      if (!offer) return;
      cell.addEventListener("mouseenter", (e) => {
        const lines = window.ResultsAnalytics?.formatOfferTooltipLines
          ? window.ResultsAnalytics.formatOfferTooltipLines(offer)
          : [`${offer.origin_name} → ${offer.out_dest_name}`, `¥${offer.price}`, `${offer.out_date} / ${offer.ret_date}`];
        showTooltip(e, lines);
      });
      cell.addEventListener("mousemove", (e) => {
        const lines = window.ResultsAnalytics?.formatOfferTooltipLines
          ? window.ResultsAnalytics.formatOfferTooltipLines(offer)
          : [];
        if (lines.length) showTooltip(e, lines);
      });
      cell.addEventListener("mouseleave", hideTooltip);
    });
  }

  function formatMatrixDateMeta(meta) {
    const outStart = meta?.out_date_start || "";
    const outEnd = meta?.out_date_end || outStart;
    const retStart = meta?.ret_date_start || "";
    const retEnd = meta?.ret_date_end || retStart;
    if (outStart === retStart && outEnd === retEnd) {
      return `日期窗口 ${outStart} ~ ${outEnd}（穷举去程×返程组合）`;
    }
    return `去程 ${outStart} ~ ${outEnd} · 返程 ${retStart} ~ ${retEnd}`;
  }

  function renderMatrixReport({ offers, intent, meta, stats, pricingWarning }) {
    const root = document.getElementById("matrixReportRoot");
    if (!root) return;

    const routes = meta?.routes || [];
    const outDays = meta?.out_days || [];
    const retDays = meta?.ret_days || [];
    const byRoute = groupOffersByRoute(offers);
    const globalScale = computeGlobalScale(offers);
    const summaries = buildRouteSummaries(routes, byRoute, globalScale);

    const routeCount = routes.length;
    const title = intent?.title || "机票价格矩阵总览";
    const dateMeta = formatMatrixDateMeta(meta);
    const axisHint = "横轴=返程日期 · 纵轴=出发日期";

    let banner = "";
    const abnormal =
      stats?.pricing_service_abnormal || meta?.pricing_service_abnormal || pricingWarning;
    if (abnormal) {
      const detail =
        pricingWarning ||
        stats?.api_failure_message ||
        meta?.pricing_service_message ||
        "查价服务异常";
      banner = `<div class="matrix-banner-err">${detail}${stats?.api_failures ? `（${stats.api_failures} 次查价失败）` : ""}</div>`;
    }

    const legendMin =
      globalScale.max > globalScale.min
        ? `¥${Math.round(globalScale.min).toLocaleString()}`
        : "—";
    const legendMax =
      globalScale.max > globalScale.min
        ? `¥${Math.round(globalScale.max).toLocaleString()}`
        : "—";

    const cards = routes
      .map((route) => {
        const key = routeKey(route.origin, route.dest);
        return renderMatrixCard(route, byRoute.get(key) || [], outDays, retDays, globalScale);
      })
      .join("");

    root.innerHTML = `
      <div class="matrix-report">
        ${banner}
        <header class="matrix-hero">
          <div class="hero-badge" style="font-size:0.7rem;color:var(--coral);letter-spacing:0.08em">PRICE MATRIX</div>
          <h1>${title}</h1>
          <div class="matrix-hero-meta">
            有效路线 ${routeCount} 条 · 横轴=返程日期 · 纵轴=出发日期 · 币种 CNY<br/>
            ${dateMeta}
          </div>
          <div class="matrix-legend-wrap">
            <span style="font-size:0.78rem;color:var(--muted)">价格色阶</span>
            <div>
              <div class="matrix-legend-bar"></div>
              <div class="matrix-legend-labels"><span>${legendMin}</span><span>${legendMax}</span></div>
            </div>
          </div>
        </header>
        <div class="matrix-summary-row">
          ${renderSummaryTable("路线最低价汇总", summaries, "min")}
          ${renderSummaryTable("路线最高价汇总", summaries, "max")}
        </div>
        <div class="matrix-card-grid">${cards}</div>
      </div>`;

    bindCellTooltips(root, offers);
  }

  window.MatrixView = {
    render: renderMatrixReport,
    hideTooltip,
  };
})();