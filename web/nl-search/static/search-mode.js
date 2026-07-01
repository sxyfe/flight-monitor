/* 搜索模式下拉 — UiSelect */
(function () {
  function mount() {
    const el = document.getElementById("search-mode-app");
    if (!el || typeof Vue === "undefined" || !window.UiComponents) return;

    const { createApp, ref, watch } = Vue;
    const { UiSelect } = window.UiComponents;

    createApp({
      components: { UiSelect },
      setup() {
        const mode = ref("smart");
        const options = [
          { value: "smart", label: "智能精简" },
          { value: "exhaustive", label: "全量穷举" },
        ];

        watch(mode, (v) => {
          window.dispatchEvent(new CustomEvent("nl-search-mode-change", { detail: { mode: v } }));
        });

        window.SearchModeBridge = {
          getMode: () => mode.value,
          setMode: (v) => {
            mode.value = v;
          },
        };

        return { mode, options };
      },
      template: `<UiSelect v-model="mode" :options="options" />`,
    }).mount(el);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
