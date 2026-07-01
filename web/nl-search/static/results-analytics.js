/* 结果区图表聚合、索引与中文 tooltip */
(function () {
  const TOOLTIP_LIMIT = 5;

  function formatRouteLabel(o) {
    const orig = o.origin_name || o.origin;
    const out = o.out_dest_name || o.dest_name || o.out_dest;
    const retDest = o.ret_dest_name || o.ret_dest;
    const retOrig = o.ret_origin_name || o.ret_origin;
    if (o.trip_type === "open_jaw") {
      return `${orig} → ${out} · ${retDest} → ${retOrig}`;
    }
    return `${orig} ⇄ ${out}`;
  }

  function formatOfferTooltipLines(o) {
    const type = o.trip_type === "open_jaw" ? "开口程" : "往返";
    const lines = [`[${type}] ${formatRouteLabel(o)} · ¥${o.price}`];
    lines.push(`去程 ${o.out_date} · 回程 ${o.ret_date || "-"} · 停留 ${o.stay_days}天`);
    const detail = o.detail || "";
    if (detail) {
      detail.split("|").forEach((part) => {
        const t = part.trim();
        if (t) lines.push(t.length > 60 ? t.slice(0, 60) + "…" : t);
      });
    } else {
      if (o.summary_out) lines.push("去: " + o.summary_out);
      if (o.summary_ret) lines.push("回: " + o.summary_ret);
    }
    return lines;
  }

  function formatTooltipOffers(matched) {
    if (!matched?.length) return ["（无明细）"];
    const lines = [];
    matched.slice(0, TOOLTIP_LIMIT).forEach((o) => {
      lines.push("——");
      lines.push(...formatOfferTooltipLines(o));
    });
    if (matched.length > TOOLTIP_LIMIT) {
      lines.push(`——`);
      lines.push(`还有 ${matched.length - TOOLTIP_LIMIT} 条`);
    }
    return lines;
  }

  function aggregateClient(offers) {
    if (!offers.length) {
      return {
        by_price_bucket: [],
        by_stay_days: [],
        by_destination: [],
        by_origin: [],
        by_trip_type: [],
      };
    }
    const buckets = {};
    offers.forEach((o) => {
      const b = Math.floor(o.price / 100) * 100;
      const key = `${b}-${b + 99}`;
      buckets[key] = (buckets[key] || 0) + 1;
    });
    const stay = {};
    offers.forEach((o) => {
      const d = o.stay_days;
      if (!stay[d] || o.price < stay[d].min_price) {
        stay[d] = { days: d, count: 0, min_price: o.price };
      }
      stay[d].count += 1;
    });
    const dest = {};
    offers.forEach((o) => {
      const code = o.out_dest || o.dest || "";
      const name = o.out_dest_name || o.dest_name || code;
      if (!code) return;
      if (!dest[code] || o.price < dest[code].min_price) {
        dest[code] = { code, name, count: 0, min_price: o.price };
      }
      dest[code].count += 1;
    });
    const origin = {};
    offers.forEach((o) => {
      const code = o.origin;
      if (!code) return;
      if (!origin[code] || o.price < origin[code].min_price) {
        origin[code] = {
          code,
          name: o.origin_name || code,
          count: 0,
          min_price: o.price,
        };
      }
      origin[code].count += 1;
    });
    const rt = offers.filter((o) => o.trip_type === "round_trip").length;
    const oj = offers.filter((o) => o.trip_type === "open_jaw").length;
    return {
      by_price_bucket: Object.entries(buckets)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([bucket, count]) => ({ bucket, count })),
      by_stay_days: Object.values(stay).sort((a, b) => a.days - b.days),
      by_destination: Object.values(dest).sort((a, b) => a.min_price - b.min_price),
      by_origin: Object.values(origin).sort((a, b) => a.min_price - b.min_price),
      by_trip_type: [
        { type: "round_trip", count: rt },
        { type: "open_jaw", count: oj },
      ],
    };
  }

  function buildOfferIndexes(offers) {
    const byPriceBucket = {};
    const byStayDays = {};
    const byOutDest = {};
    const byTripType = { round_trip: [], open_jaw: [] };
    const byOutDate = {};
    const byRetDate = {};
    const byOriginName = {};
    const byRouteKey = {};
    const byDatePair = {};

    offers.forEach((o) => {
      const b = Math.floor(o.price / 100) * 100;
      const bucket = `${b}-${b + 99}`;
      (byPriceBucket[bucket] ||= []).push(o);

      const sd = String(o.stay_days);
      (byStayDays[sd] ||= []).push(o);

      const destCode = o.out_dest || o.dest || "";
      const destName = o.out_dest_name || o.dest_name || destCode;
      (byOutDest[destName] ||= []).push(o);
      if (destCode) (byOutDest[destCode] ||= []).push(o);

      if (o.trip_type === "open_jaw") byTripType.open_jaw.push(o);
      else byTripType.round_trip.push(o);

      if (o.out_date) (byOutDate[o.out_date] ||= []).push(o);
      if (o.ret_date) (byRetDate[o.ret_date] ||= []).push(o);
      if (o.origin_name) (byOriginName[o.origin_name] ||= []).push(o);

      const route = formatRouteLabel(o);
      (byRouteKey[route] ||= []).push(o);

      const pairKey = `${o.out_date}|${o.ret_date || ""}`;
      if (!byDatePair[pairKey] || o.price < byDatePair[pairKey].price) {
        byDatePair[pairKey] = o;
      }
    });

    Object.values(byPriceBucket).forEach((arr) => arr.sort((a, b) => a.price - b.price));
    Object.values(byStayDays).forEach((arr) => arr.sort((a, b) => a.price - b.price));
    Object.values(byOutDest).forEach((arr) => arr.sort((a, b) => a.price - b.price));
    Object.values(byOutDate).forEach((arr) => arr.sort((a, b) => a.price - b.price));
    Object.values(byRetDate).forEach((arr) => arr.sort((a, b) => a.price - b.price));
    Object.values(byOriginName).forEach((arr) => arr.sort((a, b) => a.price - b.price));
    Object.values(byRouteKey).forEach((arr) => arr.sort((a, b) => a.price - b.price));

    return {
      byPriceBucket,
      byStayDays,
      byOutDest,
      byTripType,
      byOutDate,
      byRetDate,
      byOriginName,
      byRouteKey,
      byDatePair,
    };
  }

  function minByKey(list, key) {
    const m = {};
    list.forEach((o) => {
      const k = o[key];
      if (!k) return;
      if (!(k in m) || o.price < m[k].price) m[k] = o;
    });
    return Object.values(m).sort((a, b) => (a[key] || "").localeCompare(b[key] || ""));
  }

  function chartTooltipCallbacks(getMatched) {
    return {
      callbacks: {
        afterBody(items) {
          if (!items?.length) return [];
          const idx = items[0].dataIndex;
          const matched = getMatched(idx, items[0].label);
          return formatTooltipOffers(matched);
        },
      },
    };
  }

  window.ResultsAnalytics = {
    TOOLTIP_LIMIT,
    formatRouteLabel,
    formatOfferTooltipLines,
    formatTooltipOffers,
    aggregateClient,
    buildOfferIndexes,
    minByKey,
    chartTooltipCallbacks,
  };
})();
