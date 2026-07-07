/* shadcn 风格 Vue 轻量组件 — CDN 无构建 */
(function () {
  if (typeof Vue === "undefined") return;

  const { defineComponent, ref, computed, onMounted, onBeforeUnmount } = Vue;

  const UiInput = defineComponent({
    name: "UiInput",
    props: {
      modelValue: { type: [String, Number], default: "" },
      type: { type: String, default: "text" },
      placeholder: { type: String, default: "" },
      min: { type: [String, Number], default: undefined },
      step: { type: [String, Number], default: undefined },
    },
    emits: ["update:modelValue", "input"],
    setup(props, { emit }) {
      const onInput = (e) => {
        const v = props.type === "number" ? Number(e.target.value) : e.target.value;
        emit("update:modelValue", v);
        emit("input", v);
      };
      return { onInput };
    },
    template: `
      <input
        class="ui-input"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :min="min"
        :step="step"
        @input="onInput"
      />
    `,
  });

  const UiTextarea = defineComponent({
    name: "UiTextarea",
    props: {
      modelValue: { type: String, default: "" },
      placeholder: { type: String, default: "" },
      rows: { type: Number, default: 3 },
    },
    emits: ["update:modelValue", "input"],
    setup(props, { emit }) {
      const onInput = (e) => {
        emit("update:modelValue", e.target.value);
        emit("input", e.target.value);
      };
      return { onInput };
    },
    template: `
      <textarea
        class="ui-textarea"
        :rows="rows"
        :value="modelValue"
        :placeholder="placeholder"
        @input="onInput"
      ></textarea>
    `,
  });

  const UiButton = defineComponent({
    name: "UiButton",
    props: {
      variant: { type: String, default: "primary" },
      size: { type: String, default: "md" },
      disabled: { type: Boolean, default: false },
      type: { type: String, default: "button" },
    },
    emits: ["click"],
    template: `
      <button
        :type="type"
        class="ui-btn"
        :class="['ui-btn-' + variant, size === 'sm' ? 'ui-btn-sm' : '']"
        :disabled="disabled"
        @click="$emit('click', $event)"
      ><slot /></button>
    `,
  });

  const UiCheckbox = defineComponent({
    name: "UiCheckbox",
    props: { modelValue: { type: Boolean, default: false }, label: { type: String, default: "" } },
    emits: ["update:modelValue", "change"],
    setup(props, { emit }) {
      const toggle = (e) => {
        emit("update:modelValue", e.target.checked);
        emit("change", e.target.checked);
      };
      return { toggle };
    },
    template: `
      <label class="ui-checkbox-row">
        <input type="checkbox" :checked="modelValue" @change="toggle" />
        <span>{{ label }}</span>
      </label>
    `,
  });

  const UiMultiSelect = defineComponent({
    name: "UiMultiSelect",
    props: {
      modelValue: { type: Array, default: () => [] },
      options: { type: Array, default: () => [] },
      placeholder: { type: String, default: "选择…" },
      allowCreate: { type: Boolean, default: false },
    },
    emits: ["update:modelValue", "change"],
    setup(props, { emit }) {
      const open = ref(false);
      const filter = ref("");
      const root = ref(null);
      const chipInput = ref(null);

      const filtered = computed(() => {
        const q = filter.value.trim().toLowerCase();
        const opts = props.options.filter((o) => !props.modelValue.includes(o));
        if (!q) return opts;
        return opts.filter((o) => o.toLowerCase().includes(q));
      });

      const toggle = (val) => {
        const next = props.modelValue.includes(val)
          ? props.modelValue.filter((v) => v !== val)
          : [...props.modelValue, val];
        emit("update:modelValue", next);
        emit("change", next);
        filter.value = "";
      };

      const remove = (val, e) => {
        e?.stopPropagation();
        const next = props.modelValue.filter((v) => v !== val);
        emit("update:modelValue", next);
        emit("change", next);
      };

      const addCustom = () => {
        const v = filter.value.trim();
        if (!v || props.modelValue.includes(v)) return;
        emit("update:modelValue", [...props.modelValue, v]);
        emit("change", [...props.modelValue, v]);
        filter.value = "";
      };

      const focusField = () => {
        open.value = true;
        chipInput.value?.focus();
      };

      const onDocClick = (e) => {
        if (root.value && !root.value.contains(e.target)) open.value = false;
      };

      onMounted(() => document.addEventListener("click", onDocClick));
      onBeforeUnmount(() => document.removeEventListener("click", onDocClick));

      return { open, filter, root, chipInput, filtered, toggle, remove, addCustom, focusField };
    },
    template: `
      <div class="ui-multi-wrap" ref="root">
        <div class="ui-chip-field-wrap">
          <div class="ui-chip-field" @click="focusField">
            <span v-for="v in modelValue" :key="v" class="ui-badge">{{ v }}<button type="button" @click="remove(v, $event)">×</button></span>
            <input
              ref="chipInput"
              class="ui-chip-input"
              v-model="filter"
              :placeholder="modelValue.length ? '' : placeholder"
              @focus="open = true"
              @keydown.enter.prevent="allowCreate && filter.trim() ? addCustom() : null"
              @keydown.backspace="!filter && modelValue.length && remove(modelValue[modelValue.length - 1], $event)"
            />
          </div>
        </div>
        <div v-if="open" class="ui-multi-panel" @click.stop>
          <button v-for="o in filtered" :key="o" type="button" class="ui-multi-option" @click="toggle(o)">{{ o }}</button>
          <button v-if="allowCreate && filter.trim() && !options.includes(filter.trim()) && !modelValue.includes(filter.trim())" type="button" class="ui-multi-option" @click="addCustom">添加「{{ filter.trim() }}」</button>
          <p v-if="!filtered.length && !(allowCreate && filter.trim())" class="ui-hint" style="padding:8px 12px;margin:0">无匹配项</p>
        </div>
      </div>
    `,
  });

  const UiSelect = defineComponent({
    name: "UiSelect",
    props: {
      modelValue: { type: String, default: "" },
      options: { type: Array, default: () => [] },
      placeholder: { type: String, default: "选择…" },
    },
    emits: ["update:modelValue", "change"],
    setup(props, { emit }) {
      const open = ref(false);
      const root = ref(null);

      const label = computed(() => {
        const hit = props.options.find((o) => o.value === props.modelValue);
        return hit ? hit.label : props.placeholder;
      });

      const pick = (val) => {
        emit("update:modelValue", val);
        emit("change", val);
        open.value = false;
      };

      const onDocClick = (e) => {
        if (root.value && !root.value.contains(e.target)) open.value = false;
      };

      onMounted(() => document.addEventListener("click", onDocClick));
      onBeforeUnmount(() => document.removeEventListener("click", onDocClick));

      return { open, root, label, pick };
    },
    template: `
      <div class="ui-select-wrap" ref="root">
        <button type="button" class="ui-select-trigger" @click.stop="open = !open">{{ label }}</button>
        <div v-if="open" class="ui-multi-panel" @click.stop>
          <button
            v-for="o in options"
            :key="o.value"
            type="button"
            class="ui-multi-option"
            :class="{ 'is-selected': modelValue === o.value }"
            @click="pick(o.value)"
          >{{ o.label }}</button>
        </div>
      </div>
    `,
  });

  const UiDateRange = defineComponent({
    name: "UiDateRange",
    props: {
      modelValue: { type: Array, default: () => [] },
      minDate: { type: String, default: "" },
    },
    emits: ["update:modelValue", "change"],
    setup(props, { emit }) {
      const start = computed({
        get: () => props.modelValue?.[0] || "",
        set(v) {
          const end = props.modelValue?.[1] || "";
          emit("update:modelValue", [v, end]);
          emit("change", [v, end]);
        },
      });
      const end = computed({
        get: () => props.modelValue?.[1] || "",
        set(v) {
          const s = props.modelValue?.[0] || "";
          emit("update:modelValue", [s, v]);
          emit("change", [s, v]);
        },
      });
      return { start, end };
    },
    template: `
      <div class="ui-date-range-wrap">
        <div class="ui-date-range">
          <input type="date" :min="minDate" v-model="start" aria-label="开始日期" />
          <span class="ui-date-sep">至</span>
          <input type="date" :min="start || minDate" v-model="end" aria-label="结束日期" />
        </div>
      </div>
    `,
  });

  window.UiComponents = {
    UiInput,
    UiTextarea,
    UiButton,
    UiCheckbox,
    UiMultiSelect,
    UiSelect,
    UiDateRange,
  };
})();
