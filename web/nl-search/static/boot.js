/* 依赖自检（脚本已在 index.html 按序同步加载，此处仅兜底提示） */
(function () {
  function showEditorError(msg) {
    const el = document.getElementById("intent-editor-app");
    if (el && !el.__vue_app__) {
      el.innerHTML =
        '<p style="color:#dc2626;padding:12px;background:#fef2f2;border-radius:8px;font-size:14px">' +
        msg +
        "</p>";
    }
  }

  if (typeof Vue === "undefined") {
    showEditorError("Vue 未加载，请硬刷新（Cmd+Shift+R）并确认 /static/vendor/vue.global.js 可访问。");
  } else if (!window.UiComponents) {
    showEditorError("UI 组件未加载，请硬刷新页面。");
  }
})();
