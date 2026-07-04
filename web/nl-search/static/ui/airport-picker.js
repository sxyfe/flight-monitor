/* 机场中文搜索选择器 — chip 内嵌输入框 */
(function () {
  if (typeof Vue === "undefined" || !window.UiComponents) return;

  const { defineComponent, ref, onBeforeUnmount } = Vue;

  function formatAirportLabel(item) {
    const parts = [];
    if (item?.countryName) parts.push(item.countryName);
    const city = [item?.cityName, item?.cityCode ? `(${item.cityCode})` : ""].filter(Boolean).join(" ");
    if (city) parts.push(city);
    if (item?.airportName && item.airportName !== item.cityName) parts.push(item.airportName);
    return parts.join(" · ") || item?.cityCode || "";
  }

  window.AirportPicker = defineComponent({
    name: "AirportPicker",
    props: {
      modelValue: { type: Array, default: () => [] },
      labels: { type: Object, default: () => ({}) },
      placeholder: { type: String, default: "城市、机场名或三字码（中文需 RollingGo Key）" },
    },
    emits: ["update:modelValue", "update:labels", "dirty"],
    setup(props, { emit }) {
      const keyword = ref("");
      const suggestions = ref([]);
      const open = ref(false);
      const loading = ref(false);
      const apiError = ref("");
      const apiWarning = ref("");
      const chipInput = ref(null);
      let timer = null;

      const AUTH_CODES = new Set(["NOT_CONFIGURED", "ROLLINGGO_AUTH"]);

      const search = (q) => {
        clearTimeout(timer);
        apiError.value = "";
        apiWarning.value = "";
        if (!q.trim()) {
          suggestions.value = [];
          open.value = false;
          return;
        }
        timer = setTimeout(() => {
          loading.value = true;
          fetch(window.apiUrl(`/api/airport/search?q=${encodeURIComponent(q.trim())}`))
            .then(async (r) => {
              const d = await r.json().catch(() => ({}));
              const items = (d.items || []).map((item) => ({
                ...item,
                label: formatAirportLabel(item),
              }));
              if (!items.length) {
                apiWarning.value = "";
                suggestions.value = [];
                open.value = false;
                apiError.value =
                  d.error && AUTH_CODES.has(d.code) ? d.error : "未搜索到机场";
                return;
              }
              if (!r.ok || d.error) {
                apiError.value = d.error || `机场搜索失败（${r.status}）`;
                apiWarning.value = "";
                suggestions.value = [];
                open.value = false;
                return;
              }
              apiWarning.value = d.warning || "";
              suggestions.value = items;
              open.value = true;
            })
            .catch(() => {
              apiError.value = "机场搜索请求失败";
              suggestions.value = [];
            })
            .finally(() => {
              loading.value = false;
            });
        }, 280);
      };

      const onInput = (e) => {
        keyword.value = e.target.value;
        emit("dirty");
        search(keyword.value);
      };

      const focusField = () => {
        chipInput.value?.focus();
      };

      const addCode = (item) => {
        if (!item?.cityCode || props.modelValue.includes(item.cityCode)) return;
        emit("update:modelValue", [...props.modelValue, item.cityCode]);
        emit("update:labels", {
          ...props.labels,
          [item.cityCode]: item.cityName || item.cityCode,
        });
        emit("dirty");
        keyword.value = "";
        suggestions.value = [];
        open.value = false;
        apiError.value = "";
        apiWarning.value = "";
      };

      const remove = (code, e) => {
        e?.stopPropagation();
        emit(
          "update:modelValue",
          props.modelValue.filter((c) => c !== code)
        );
        emit("dirty");
      };

      onBeforeUnmount(() => clearTimeout(timer));

      return {
        keyword,
        suggestions,
        open,
        loading,
        apiError,
        apiWarning,
        chipInput,
        onInput,
        focusField,
        addCode,
        remove,
      };
    },
    template: `
      <div class="ui-chip-field-wrap" style="position:relative;margin-bottom:0">
        <div class="ui-chip-field" @click="focusField">
          <span v-for="code in modelValue" :key="code" class="ui-badge">{{ labels[code] || code }} · {{ code }}<button type="button" @click="remove(code, $event)">×</button></span>
          <input
            ref="chipInput"
            class="ui-chip-input"
            type="text"
            :value="keyword"
            :placeholder="modelValue.length ? '' : placeholder"
            @input="onInput"
          />
        </div>
        <div v-if="open && suggestions.length" class="ui-suggest-list">
          <button v-for="item in suggestions" :key="item.cityCode + (item.airportCode||'')" type="button" class="ui-suggest-item" @click="addCode(item)">{{ item.label }}</button>
        </div>
        <div v-if="loading" class="ui-hint">搜索中…</div>
        <div v-else-if="apiError" class="ui-hint ui-hint-err">{{ apiError }}</div>
        <div v-else-if="apiWarning" class="ui-hint">{{ apiWarning }}</div>
      </div>
    `,
  });
})();
