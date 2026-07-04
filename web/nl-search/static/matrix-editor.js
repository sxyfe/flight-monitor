/* 价格矩阵查询表单 */
(function () {
  function mountMatrixEditor() {
    if (!document.getElementById("matrix-editor-app")) return;
    if (typeof Vue === "undefined" || !window.UiComponents || !window.AirportPicker) {
      const el = document.getElementById("matrix-editor-app");
      if (el) el.innerHTML = '<p class="ui-msg ui-msg-err">组件未就绪，请刷新页面。</p>';
      return;
    }

    const { createApp, reactive, ref } = Vue;
    const AirportPicker = window.AirportPicker;

    function todayStr() {
      const t = new Date();
      return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    }

    function defaultForm() {
      return {
        origins: [],
        originLabels: {},
        destinations: [],
        destLabels: {},
        outDateStart: "",
        outDateEnd: "",
        retDateStart: "",
        retDateEnd: "",
        dateMode: "range",
        minStayDays: 1,
        maxStayDays: "",
      };
    }

    function stayFields(form) {
      const min = Number(form.minStayDays) || 1;
      const maxRaw = form.maxStayDays;
      const max =
        maxRaw === "" || maxRaw == null ? null : Number(maxRaw);
      return { min_stay_days: min, max_stay_days: max };
    }

    function formToIntent(form) {
      const stay = stayFields(form);
      const outStart = form.outDateStart || "";
      if (form.dateMode === "window") {
        const windowEnd = form.retDateEnd || "";
        return {
          origins: form.origins,
          destinations: form.destinations,
          origin_labels: form.originLabels,
          dest_labels: form.destLabels,
          out_date: outStart,
          ret_date: windowEnd,
          out_date_start: outStart,
          out_date_end: windowEnd,
          ret_date_start: outStart,
          ret_date_end: windowEnd,
          ...stay,
          cabin: "ECONOMY",
          adults: 1,
          children: 0,
        };
      }
      const outEnd = form.outDateEnd || outStart;
      const retStart = form.retDateStart || "";
      const retEnd = form.retDateEnd || retStart;
      return {
        origins: form.origins,
        destinations: form.destinations,
        origin_labels: form.originLabels,
        dest_labels: form.destLabels,
        out_date_start: outStart,
        out_date_end: outEnd,
        ret_date_start: retStart,
        ret_date_end: retEnd,
        ...stay,
        cabin: "ECONOMY",
        adults: 1,
        children: 0,
      };
    }

    const app = createApp({
      components: { AirportPicker },
      setup() {
        const form = reactive(defaultForm());
        const validation = ref(null);
        const msg = ref("");
        const msgType = ref("");
        const minDate = todayStr();

        function openDatePicker(e) {
          const el = e.currentTarget;
          if (typeof el.showPicker === "function") {
            try {
              el.showPicker();
            } catch (_) {
              /* 已展开或不支持时忽略 */
            }
          }
        }

        function setDateMode(mode) {
          form.dateMode = mode;
          if (mode === "window" && form.outDateStart && form.retDateEnd) {
            form.outDateEnd = form.retDateEnd;
            form.retDateStart = form.outDateStart;
          }
        }

        return { form, validation, msg, msgType, minDate, openDatePicker, setDateMode };
      },
      template: `
        <div class="matrix-form">
          <p class="parse-hint matrix-form-hint">
            多出发地 × 多目的地；穷举去程×返程日期组合（纵轴=出发、横轴=返程）。
          </p>
          <div class="matrix-date-mode" role="tablist" aria-label="日期模式">
            <button type="button" class="matrix-mode-btn" :class="{ active: form.dateMode === 'range' }" @click="setDateMode('range')">独立范围</button>
            <button type="button" class="matrix-mode-btn" :class="{ active: form.dateMode === 'window' }" @click="setDateMode('window')">共用窗口</button>
          </div>
          <div class="form-row-compact matrix-locations">
            <div class="ui-field">
              <span class="ui-label">出发地</span>
              <AirportPicker
                v-model="form.origins"
                v-model:labels="form.originLabels"
                placeholder="添加出发城市"
              />
            </div>
            <div class="ui-field">
              <span class="ui-label">目的地</span>
              <AirportPicker
                v-model="form.destinations"
                v-model:labels="form.destLabels"
                placeholder="添加目的地"
              />
            </div>
          </div>
          <template v-if="form.dateMode === 'range'">
            <div class="form-row-compact matrix-dates">
              <div class="ui-field">
                <span class="ui-label">去程起始</span>
                <input class="ui-input ui-date-input" type="date" v-model="form.outDateStart" :min="minDate" aria-label="去程起始日期" @click="openDatePicker" />
              </div>
              <div class="ui-field">
                <span class="ui-label">去程结束</span>
                <input class="ui-input ui-date-input" type="date" v-model="form.outDateEnd" :min="form.outDateStart || minDate" aria-label="去程结束日期" @click="openDatePicker" />
              </div>
            </div>
            <div class="form-row-compact matrix-dates">
              <div class="ui-field">
                <span class="ui-label">返程起始</span>
                <input class="ui-input ui-date-input" type="date" v-model="form.retDateStart" :min="form.outDateStart || minDate" aria-label="返程起始日期" @click="openDatePicker" />
              </div>
              <div class="ui-field">
                <span class="ui-label">返程结束</span>
                <input class="ui-input ui-date-input" type="date" v-model="form.retDateEnd" :min="form.retDateStart || form.outDateStart || minDate" aria-label="返程结束日期" @click="openDatePicker" />
              </div>
            </div>
          </template>
          <template v-else>
            <div class="form-row-compact matrix-dates">
              <div class="ui-field">
                <span class="ui-label">窗口起始（去程）</span>
                <input class="ui-input ui-date-input" type="date" v-model="form.outDateStart" :min="minDate" aria-label="窗口起始日期" @click="openDatePicker" />
              </div>
              <div class="ui-field">
                <span class="ui-label">窗口结束（返程）</span>
                <input class="ui-input ui-date-input" type="date" v-model="form.retDateEnd" :min="form.outDateStart || minDate" aria-label="窗口结束日期" @click="openDatePicker" />
              </div>
            </div>
            <p class="parse-hint matrix-form-hint matrix-window-hint">两轴共用同一日期窗口，适合「国庆前后」等连续区间扫价。</p>
          </template>
          <div class="form-row-compact matrix-stay">
            <div class="ui-field">
              <span class="ui-label">最少停留（天）</span>
              <input class="ui-input" type="number" min="1" v-model.number="form.minStayDays" aria-label="最少停留天数" />
            </div>
            <div class="ui-field">
              <span class="ui-label">最多停留（天）</span>
              <input class="ui-input" type="number" min="1" v-model="form.maxStayDays" placeholder="不限" aria-label="最多停留天数" />
            </div>
          </div>
          <p v-if="msg" class="ui-msg" :class="'ui-msg-' + (msgType || 'ok')">{{ msg }}</p>
        </div>
      `,
    });

    const vm = app.mount("#matrix-editor-app");

    window.MatrixEditorBridge = {
      getIntent() {
        return formToIntent(vm.form);
      },
      async validateIntent() {
        vm.msg = "";
        vm.msgType = "";
        const intent = formToIntent(vm.form);
        try {
          const res = await fetch(window.apiUrl("/api/matrix/validate"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ intent }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            const detail = data.detail && typeof data.detail === "object" ? data.detail : data;
            const v = detail.validation || data.validation;
            vm.validation = v || null;
            const errText =
              v?.errors?.join("；") ||
              (typeof detail === "string" ? detail : null) ||
              (typeof data.detail === "string" ? data.detail : null) ||
              "校验失败";
            vm.msg = errText;
            vm.msgType = "err";
            return { ok: false, message: errText, intent, validation: v };
          }
          vm.validation = data.validation;
          if (data.validation?.warnings?.length) {
            vm.msg = data.validation.warnings.join("；");
            vm.msgType = "warn";
          }
          if (!data.validation?.valid) {
            const errText = data.validation.errors?.join("；") || "请完善条件";
            vm.msg = errText;
            vm.msgType = "err";
            return { ok: false, message: errText, intent, validation: data.validation };
          }
          return { ok: true, intent, validation: data.validation };
        } catch (e) {
          vm.msg = e.message || "校验失败";
          vm.msgType = "err";
          return { ok: false, message: vm.msg, intent };
        }
      },
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountMatrixEditor);
  } else {
    mountMatrixEditor();
  }
})();
