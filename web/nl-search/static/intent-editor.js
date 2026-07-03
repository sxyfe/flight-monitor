/* 意图表单编辑器 — shadcn 风格 + 查询字符串 */
(function () {
  function mountEditor() {
    if (!document.getElementById("intent-editor-app")) return;
    if (typeof Vue === "undefined" || !window.UiComponents || !window.IntentQuery) {
      const el = document.getElementById("intent-editor-app");
      if (el) el.innerHTML = '<p class="ui-msg ui-msg-err">组件未就绪，请刷新页面。</p>';
      return;
    }

    const { createApp, ref, reactive, watch, computed } = Vue;
    const { UiInput, UiTextarea, UiButton, UiCheckbox, UiMultiSelect, UiDateRange } = window.UiComponents;
    const AirportPicker = window.AirportPicker;

    const COUNTRY_OPTIONS = ["泰国", "菲律宾", "印度尼西亚", "马来西亚", "日本"];

    function defaultForm() {
      return {
        origins: [],
        originLabels: {},
        destinations: [],
        destLabels: {},
        countries: [],
        dateRange: [],
        min_stay_days: 7,
        max_stay_days: null,
        max_price: null,
        rt: true,
        oj: true,
        queryText: "",
      };
    }

    function intentToForm(intent) {
      const labels = {};
      (intent.origins || []).forEach((c) => {
        labels[c] = c;
      });
      const destLabels = {};
      (intent.destinations || []).forEach((c) => {
        destLabels[c] = c;
      });
      return {
        origins: [...(intent.origins || [])],
        originLabels: labels,
        destinations: [...(intent.destinations || [])],
        destLabels,
        countries: [...(intent.countries || [])],
        dateRange: intent.date_start && intent.date_end ? [intent.date_start, intent.date_end] : [],
        min_stay_days: intent.min_stay_days || 7,
        max_stay_days: intent.max_stay_days ?? null,
        max_price: intent.max_price ?? null,
        rt: (intent.trip_modes || []).includes("round_trip"),
        oj: (intent.trip_modes || []).includes("open_jaw"),
        queryText: "",
      };
    }

    function formToIntent(form) {
      const trip_modes = [];
      if (form.rt) trip_modes.push("round_trip");
      if (form.oj) trip_modes.push("open_jaw");
      return {
        origins: form.origins,
        destinations: form.destinations,
        countries: form.countries,
        date_start: form.dateRange?.[0] || "",
        date_end: form.dateRange?.[1] || "",
        min_stay_days: Number(form.min_stay_days) || 7,
        max_stay_days:
          form.max_stay_days === "" || form.max_stay_days == null
            ? null
            : Number(form.max_stay_days),
        max_price: form.max_price === "" || form.max_price == null ? null : Number(form.max_price),
        trip_modes,
        cabin: "ECONOMY",
        adults: 1,
        children: 0,
      };
    }

    function todayStr() {
      const t = new Date();
      const y = t.getFullYear();
      const m = String(t.getMonth() + 1).padStart(2, "0");
      const d = String(t.getDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    }

    const app = createApp({
      components: {
        AirportPicker,
        UiInput,
        UiTextarea,
        UiButton,
        UiCheckbox,
        UiMultiSelect,
        UiDateRange,
      },
      setup() {
        const form = reactive(defaultForm());
        const formDirty = ref(false);
        const queryDirty = ref(false);
        const syncingQuery = ref(false);
        const validation = ref(null);
        const msg = ref("");
        const msgType = ref("ok");
        const reparseLoading = ref(false);
        const minDate = todayStr();
        const countryCounts = ref({});

        const refreshCountryCounts = async () => {
          const next = {};
          for (const c of form.countries || []) {
            try {
              const res = await fetch(
                window.apiUrl(
                  `/api/country/${encodeURIComponent(c)}/airports?mode=exhaustive`
                )
              );
              if (res.ok) {
                const data = await res.json();
                next[c] = { exhaustive: data.count };
              }
            } catch (_) {}
          }
          countryCounts.value = next;
        };

        const syncQueryFromForm = () => {
          syncingQuery.value = true;
          const intent = formToIntent(form);
          form.queryText = window.IntentQuery.intentToQueryString(intent, {
            originLabels: form.originLabels,
            destLabels: form.destLabels,
          });
          queryDirty.value = false;
          syncingQuery.value = false;
        };

        watch(
          () => [...(form.countries || [])],
          () => {
            refreshCountryCounts();
          },
          { immediate: true }
        );

        watch(
          () => [
            form.origins,
            form.destinations,
            form.countries,
            form.dateRange,
            form.min_stay_days,
            form.max_stay_days,
            form.max_price,
            form.rt,
            form.oj,
            form.originLabels,
            form.destLabels,
          ],
          () => {
            if (syncingQuery.value) return;
            if (!queryDirty.value) syncQueryFromForm();
          },
          { deep: true }
        );

        const markFormDirty = () => {
          formDirty.value = true;
        };

        const setMaxStay = (v) => {
          if (v === "" || v == null || Number.isNaN(Number(v))) {
            form.max_stay_days = null;
          } else {
            form.max_stay_days = Number(v);
          }
          markFormDirty();
        };

        const onQueryInput = () => {
          if (!syncingQuery.value) queryDirty.value = true;
        };

        const syncFormFromIntent = (intent) => {
          Object.assign(form, intentToForm(intent));
          formDirty.value = false;
          syncQueryFromForm();
        };

        const loadIntent = (intent, nextValidation = null) => {
          syncFormFromIntent(intent);
          validation.value = nextValidation;
          msg.value = "";
        };

        const reparseQuery = async () => {
          const q = form.queryText.trim();
          if (!q) {
            msg.value = "请先填写查询字符串";
            msgType.value = "err";
            return;
          }
          reparseLoading.value = true;
          msg.value = "";
          try {
            const res = await fetch(window.apiUrl("/api/intent/parse"), {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ query: q }),
            });
            const text = await res.text();
            let data = {};
            try {
              data = text ? JSON.parse(text) : {};
            } catch (_) {
              throw new Error(text.trim().slice(0, 120) || "解析失败");
            }
            if (!res.ok) throw new Error(data.detail || "解析失败");
            syncFormFromIntent(data.intent);
            validation.value = data.validation;
            formDirty.value = false;
            msg.value = data.validation.valid ? "已重新解析并同步表单" : "已解析，请核对表单后开始搜索";
            msgType.value = data.validation.valid ? "ok" : "warn";
          } catch (e) {
            msg.value = e.message || "重新解析失败";
            msgType.value = "err";
          } finally {
            reparseLoading.value = false;
          }
        };

        const emitStatus = () => {
          window.dispatchEvent(
            new CustomEvent("nl-intent-status", { detail: { msg: msg.value, msgType: msgType.value } })
          );
        };

        const validateIntent = async () => {
          msg.value = "";
          if (queryDirty.value) {
            msg.value = "查询字符串已修改，请先重解析或恢复自动同步";
            msgType.value = "warn";
            emitStatus();
            return { ok: false, intent: null, message: msg.value, msgType: msgType.value };
          }
          if (!form.rt && !form.oj) {
            msg.value = "请至少选择一种行程类型";
            msgType.value = "err";
            emitStatus();
            return { ok: false, intent: null, message: msg.value, msgType: msgType.value };
          }
          const intent = formToIntent(form);

          let data;
          try {
            const res = await fetch(window.apiUrl("/api/intent/validate"), {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ intent }),
            });
            const text = await res.text();
            try {
              data = text ? JSON.parse(text) : {};
            } catch (_) {
              throw new Error(text.trim().slice(0, 120) || "校验失败");
            }
            if (!res.ok) throw new Error(data.detail || "校验失败");
          } catch (e) {
            msg.value = e.message || "校验失败";
            msgType.value = "err";
            emitStatus();
            return { ok: false, intent: null, message: msg.value, msgType: msgType.value };
          }

          validation.value = data.validation;
          syncFormFromIntent(intent);
          formDirty.value = false;

          if (!data.validation.valid) {
            msg.value = [...(data.validation.errors || []), ...(data.validation.clarifications || [])].join("；");
            msgType.value = "warn";
            emitStatus();
            return {
              ok: false,
              intent: null,
              validation: data.validation,
              message: msg.value,
              msgType: msgType.value,
            };
          }

          msg.value = "";
          emitStatus();
          return { ok: true, intent, validation: data.validation, message: "", msgType: "ok" };
        };

        window.IntentEditorBridge = {
          loadIntent,
          validateIntent,
          getQueryString: () => form.queryText,
        };

        syncQueryFromForm();

        return {
          form,
          COUNTRY_OPTIONS,
          validation,
          msg,
          msgType,
          minDate,
          markFormDirty,
          onQueryInput,
          reparseQuery,
          reparseLoading,
          queryDirty,
          setMaxStay,
          countryCounts,
        };
      },
      template: `
        <div>
          <div class="form-row-origins">
            <div class="ui-field">
              <span class="ui-label">出发地（中文搜索）</span>
              <AirportPicker v-model="form.origins" v-model:labels="form.originLabels" placeholder="如：北京、天津" @dirty="markFormDirty" />
            </div>
            <div class="ui-field">
              <span class="ui-label">目的地（留空按国家扩城）</span>
              <AirportPicker v-model="form.destinations" v-model:labels="form.destLabels" placeholder="如：东京、大阪" @dirty="markFormDirty" />
            </div>
          </div>
          <div class="form-grid-3">
            <div class="ui-field">
              <span class="ui-label">最少停留（天）</span>
              <UiInput v-model="form.min_stay_days" type="number" :min="1" @input="markFormDirty" />
            </div>
            <div class="ui-field">
              <span class="ui-label">最多停留（天）</span>
              <UiInput
                :model-value="form.max_stay_days ?? ''"
                type="number"
                :min="1"
                placeholder="不限"
                @update:model-value="setMaxStay"
              />
            </div>
            <div class="ui-field">
              <span class="ui-label">最高价格（元）</span>
              <UiInput v-model="form.max_price" type="number" :min="0" :step="100" @input="markFormDirty" />
            </div>
          </div>
          <div class="form-row-compact">
            <div class="ui-field">
              <span class="ui-label">国家（多选，可搜索或输入新国家）</span>
              <UiMultiSelect v-model="form.countries" :options="COUNTRY_OPTIONS" allow-create placeholder="选择或输入国家" @change="markFormDirty" />
            </div>
            <div class="ui-field">
              <span class="ui-label">出发日期范围</span>
              <UiDateRange v-model="form.dateRange" :min-date="minDate" @change="markFormDirty" />
            </div>
          </div>
          <div class="ui-field">
            <span class="ui-label">行程类型</span>
            <div style="display:flex;gap:16px;flex-wrap:wrap">
              <UiCheckbox v-model="form.rt" label="往返联票" @change="markFormDirty" />
              <UiCheckbox v-model="form.oj" label="开口程" @change="markFormDirty" />
            </div>
          </div>
          <div class="ui-field">
            <span class="ui-label">查询字符串（可编辑，改后请重解析）</span>
            <UiTextarea v-model="form.queryText" :rows="3" placeholder="由表单自动生成，也可手动编辑后重新解析" @input="onQueryInput" />
            <div class="query-reparse-row">
              <UiButton variant="secondary" size="sm" :disabled="reparseLoading" @click="reparseQuery">{{ reparseLoading ? '解析中…' : '重解析' }}</UiButton>
            </div>
            <p v-if="queryDirty" class="ui-hint">查询字符串与表单不同步，请重解析或继续编辑表单以恢复自动同步</p>
          </div>
          <p v-if="validation" class="ui-hint" style="margin-top:10px">
            智能精简预估 {{ validation.estimated_queries_smart }} 次 · 全量穷举预估 {{ validation.estimated_queries_exhaustive }} 次
            <template v-if="form.countries.length">
              <span v-for="c in form.countries" :key="c" class="country-est-hint"> · {{ c }} 穷举约 {{ countryCounts[c]?.exhaustive ?? '…' }} 城</span>
            </template>
          </p>
          <p v-if="msg" class="ui-msg" :class="'ui-msg-' + msgType">{{ msg }}</p>
        </div>
      `,
    });

    try {
      app.mount("#intent-editor-app");
    } catch (err) {
      const el = document.getElementById("intent-editor-app");
      if (el) {
        el.innerHTML =
          '<p class="ui-msg ui-msg-err">表单组件初始化失败：' + (err.message || err) + "</p>";
      }
      console.error("intent-editor mount failed", err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountEditor);
  } else {
    mountEditor();
  }
})();
