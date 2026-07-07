/* Intent → 中文查询字符串（与 Skill NL 示例对齐） */
(function () {
  function joinLabels(codes, labels) {
    return (codes || [])
      .map((c) => labels?.[c] || c)
      .filter(Boolean)
      .join("、");
  }

  function intentToQueryString(intent, labels) {
    if (!intent) return "";
    const originLabels = labels?.originLabels || {};
    const destLabels = labels?.destLabels || {};
    const parts = [];

    const origins = joinLabels(intent.origins, originLabels);
    if (origins) parts.push(`${origins}出发`);

    const dests = joinLabels(intent.destinations, destLabels);
    const countries = (intent.countries || []).filter(Boolean);
    if (dests) {
      parts.push(`去${dests}`);
    } else if (countries.length) {
      parts.push(`去${countries.join("、")}${countries.length > 1 ? "" : ""}`);
    }

    if (intent.date_start && intent.date_end) {
      parts.push(`${intent.date_start} 至 ${intent.date_end}`);
    }

    if (intent.min_stay_days) {
      parts.push(`至少玩 ${intent.min_stay_days} 天`);
    }

    if (intent.max_stay_days != null && intent.max_stay_days !== "") {
      parts.push(`最多玩 ${intent.max_stay_days} 天`);
    }

    if (intent.max_price != null && intent.max_price !== "") {
      parts.push(`${intent.max_price} 元以内`);
    }

    const modes = intent.trip_modes || [];
    const modeParts = [];
    if (modes.includes("round_trip")) modeParts.push("往返联票");
    if (modes.includes("open_jaw")) modeParts.push("开口程");
    if (modeParts.length === 2) {
      parts.push("往返和开口程都要");
    } else if (modeParts.length === 1) {
      parts.push(modeParts[0]);
    }

    if (!dests && countries.length) {
      /* 已在上面处理国家 */
    } else if (!dests && !countries.length && origins) {
      /* 仅出发地 */
    }

    return parts.join("，");
  }

  window.IntentQuery = { intentToQueryString };
})();
