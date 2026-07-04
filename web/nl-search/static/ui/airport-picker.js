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
      placeholder: {
        type: String,
        default: "城市、机场名或三字码；多码用英文逗号分隔如 PEK,PVG,NRT",
      },
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

      const parseBatchCodes = (text) => {
        if (!text.includes(",")) return null;
        const parts = text
          .split(",")
          .map((s) => s.trim().toUpperCase())
          .filter(Boolean);
        if (!parts.length || !parts.every((p) => /^[A-Z]{3}$/.test(p))) return null;
        return parts;
      };

      const resolveAirportCode = async (code) => {
        const r = await fetch(window.apiUrl(`/api/airport/search?q=${encodeURIComponent(code)}`));
        const d = await r.json().catch(() => ({}));
        const items = (d.items || []).map((item) => ({
          ...item,
          label: formatAirportLabel(item),
        }));
        if (!items.length) return { item: null, error: d.error || "未搜索到机场" };
        const exact =
          items.find(
            (it) =>
              (it.cityCode || "").toUpperCase() === code ||
              (it.airportCode || "").toUpperCase() === code
          ) || items[0];
        return { item: exact, error: "" };
      };

      const batchAddCodes = async (codes) => {
        apiError.value = "";
        apiWarning.value = "";
        loading.value = true;
        open.value = false;
        suggestions.value = [];
        const failed = [];
        const nextCodes = [...props.modelValue];
        const nextLabels = { ...props.labels };

        for (const code of codes) {
          try {
            const { item, error } = await resolveAirportCode(code);
            if (!item?.cityCode) {
              failed.push(`${code}${error ? `（${error}）` : ""}`);
              continue;
            }
            if (nextCodes.includes(item.cityCode)) continue;
            nextCodes.push(item.cityCode);
            nextLabels[item.cityCode] = item.cityName || item.cityCode;
          } catch (_) {
            failed.push(code);
          }
        }

        if (nextCodes.length !== props.modelValue.length) {
          emit("update:modelValue", nextCodes);
          emit("update:labels", nextLabels);
          emit("dirty");
        }

        keyword.value = "";
        if (failed.length) {
          apiError.value = `未识别：${failed.join("、")}`;
        }
        loading.value = false;
      };

      const onInput = (e) => {
        keyword.value = e.target.value;
        emit("dirty");
        const batch = parseBatchCodes(keyword.value);
        if (batch) return;
        search(keyword.value);
      };

      const onKeydown = (e) => {
        if (e.key !== "Enter") return;
        const batch = parseBatchCodes(keyword.value);
        if (!batch) return;
        e.preventDefault();
        batchAddCodes(batch);
      };

      const onBlur = () => {
        const batch = parseBatchCodes(keyword.value);
        if (batch) batchAddCodes(batch);
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
        onKeydown,
        onBlur,
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
            @keydown="onKeydown"
            @blur="onBlur"
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
