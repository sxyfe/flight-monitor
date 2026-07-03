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
        outDate: "",
        retDate: "",
      };
    }

    function formToIntent(form) {
      const windowStart = form.outDate || "";
      const windowEnd = form.retDate || "";
      return {
        origins: form.origins,
        destinations: form.destinations,
        origin_labels: form.originLabels,
        dest_labels: form.destLabels,
        out_date: windowStart,
        ret_date: windowEnd,
        out_date_start: windowStart,
        out_date_end: windowEnd,
        ret_date_start: windowStart,
        ret_date_end: windowEnd,
        min_stay_days: 1,
        max_stay_days: null,
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

        return { form, validation, msg, msgType, minDate, openDatePicker };
      },
      template: `
        <div class="matrix-form">
          <p class="parse-hint matrix-form-hint">
            多出发地 × 多目的地；在去程日期至返程日期窗口内穷举所有去程×返程组合（纵轴=出发、横轴=返程）。
          </p>
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
          <div class="form-row-compact matrix-dates">
            <div class="ui-field">
              <span class="ui-label">去程日期</span>
              <input class="ui-input ui-date-input" type="date" v-model="form.outDate" :min="minDate" aria-label="去程日期（窗口起始）" @click="openDatePicker" />
            </div>
            <div class="ui-field">
              <span class="ui-label">返程日期</span>
              <input class="ui-input ui-date-input" type="date" v-model="form.retDate" :min="form.outDate || minDate" aria-label="返程日期（窗口结束）" @click="openDatePicker" />
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
