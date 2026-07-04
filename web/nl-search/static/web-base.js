/* 子路径部署时 API / SSE 前缀（网关 /nl-search，本地 standalone 为空） */
(function () {
  function readBase() {
    const meta = document.querySelector('meta[name="web-base"]');
    if (meta && meta.content != null) return meta.content;
    return window.__WEB_BASE__ || "";
  }

  window.webBase = function webBase() {
    return readBase().replace(/\/$/, "");
  };

  window.apiUrl = function apiUrl(path) {
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${window.webBase()}${p}`;
  };

  /** 网关子路径下跳转到站点根（/nl-search → /，/flight-watch → /） */
  window.siteHref = function siteHref(path) {
    const p = path.startsWith("/") ? path : `/${path}`;
    const wb = window.webBase();
    if (wb && /\/nl-search\/?$/.test(wb)) {
      return wb.replace(/\/nl-search\/?$/, "") + p;
    }
    const m = location.pathname.match(/^(.*)\/nl-search\/?/);
    if (m) return m[1] + p;
    return p;
  };
})();
