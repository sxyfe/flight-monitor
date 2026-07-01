/* SSE 结果 → flight-monitor-agent 暖色报告 payload */
(function () {
  function offerToClient(o, idx) {
    let tripType = o.trip_type || o.type || "round_trip";
    if (tripType === "rt") tripType = "round_trip";

    let detailStr = o.detail;
    if (detailStr && typeof detailStr === "object") {
      detailStr = [detailStr.out, detailStr.ret].filter(Boolean).join(" · ");
    } else {
      detailStr = (detailStr || "").replace(/\|/g, " · ");
    }

    const base = {
      out: o.out_date || o.out || "",
      ret: o.ret_date || o.ret || "",
      stay_days: o.stay_days,
      price: Number(o.price || 0),
      price_out: o.price_out != null ? Number(o.price_out) : null,
      price_ret: o.price_ret != null ? Number(o.price_ret) : null,
      summary_out: o.summary_out || null,
      summary_ret: o.summary_ret || null,
      detail: detailStr || null,
    };

    if (tripType === "round_trip") {
      const dest = o.dest || o.out_dest || "";
      return {
        ...base,
        id: idx,
        type: "round_trip",
        origin: o.origin || "",
        origin_name: o.origin_name,
        out_dest: dest,
        out_dest_name: o.out_dest_name || o.dest_name,
        ret_dest: dest,
        ret_dest_name: o.ret_dest_name || o.dest_name,
        ret_origin: o.origin || "",
        ret_origin_name: o.ret_origin_name || o.origin_name,
        bookable: Boolean(o.bookable !== false),
      };
    }

    return {
      ...base,
      id: idx,
      type: "open_jaw",
      origin: o.origin || "",
      origin_name: o.origin_name,
      out_dest: o.out_dest || "",
      out_dest_name: o.out_dest_name,
      ret_dest: o.ret_dest || "",
      ret_dest_name: o.ret_dest_name,
      ret_origin: o.ret_origin || "",
      ret_origin_name: o.ret_origin_name,
      bookable: Boolean(o.bookable),
    };
  }

  function buildLocations(offers, intent, meta) {
    const codeToCountry = { ...(meta?.code_to_country || {}) };
    const intentCountries = (intent?.countries || []).filter(Boolean);
    const defaultCountry = intentCountries.length === 1 ? intentCountries[0] : "其他";

    const origins = {};
    const destNames = {};

    offers.forEach((o) => {
      if (o.origin) origins[o.origin] = o.origin_name || o.origin;
      if (o.ret_origin) origins[o.ret_origin] = o.ret_origin_name || o.ret_origin;
      [
        ["out_dest", "out_dest_name"],
        ["dest", "dest_name"],
        ["ret_dest", "ret_dest_name"],
      ].forEach(([ck, nk]) => {
        const code = o[ck];
        if (code) destNames[code] = o[nk] || code;
      });
    });

    (intent?.origins || []).forEach((c) => {
      if (c && !origins[c]) origins[c] = c;
    });

    const destByCountry = {};
    Object.entries(destNames).forEach(([code, name]) => {
      const country = codeToCountry[code] || defaultCountry;
      if (!destByCountry[country]) destByCountry[country] = {};
      destByCountry[country][code] = { name };
    });

    return { origins, destByCountry };
  }

  function buildPayload(data) {
    const offers = data.offers || [];
    const intent = data.intent || {};
    const meta = data.meta || {};
    const { origins, destByCountry } = buildLocations(offers, intent, meta);

    return {
      meta: {
        date_range: intent.date_start && intent.date_end ? [intent.date_start, intent.date_end] : meta.date_range || ["", ""],
        max_price: intent.max_price ?? meta.max_price,
        min_stay_days: intent.min_stay_days ?? meta.min_stay_days,
        max_stay_days: intent.max_stay_days ?? meta.max_stay_days,
        search_mode: data.mode || meta.search_mode,
        generated_at: new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC",
        query_summary: data.querySummary || "",
      },
      origins,
      destinations_by_country: destByCountry,
      offers: offers.map((o, i) => offerToClient(o, i)),
    };
  }

  window.ReportBridge = {
    init(data) {
      const payload = buildPayload(data);
      if (typeof window.ReportApp !== "undefined") {
        window.ReportApp.init(payload);
      }
    },
    buildPayload,
  };
})();
