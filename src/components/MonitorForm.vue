<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { MonitorRule, MonitorRuleInput } from "@/types";

const props = defineProps<{
  initial?: MonitorRule | null;
  submitLabel: string;
}>();

const emit = defineEmits<{
  submit: [value: MonitorRuleInput];
}>();

const { t } = useI18n();

const form = reactive({
  name: "",
  tripType: "one_way" as MonitorRuleInput["tripType"],
  maxPrice: 3500,
  adultCount: 1,
  childCount: 0,
  cabinGrade: "ECONOMY",
  returnDate: "",
  segments: [{ segmentOrder: 1, fromCity: "BJS", toCity: "NRT", fromDate: "" }],
});

watch(
  () => props.initial,
  (value) => {
    if (!value) return;
    form.name = value.name;
    form.tripType = value.tripType;
    form.maxPrice = value.maxPrice;
    form.adultCount = value.adultCount;
    form.childCount = value.childCount;
    form.cabinGrade = value.cabinGrade;
    form.returnDate = value.returnDate ?? "";
    form.segments = value.segments.map((segment) => ({ ...segment }));
  },
  { immediate: true },
);

const canAddSegment = computed(
  () => form.tripType !== "round_trip" && form.segments.length < 4,
);

function addSegment() {
  if (!canAddSegment.value) return;
  form.segments.push({
    segmentOrder: form.segments.length + 1,
    fromCity: form.segments[form.segments.length - 1]?.toCity ?? "",
    toCity: "",
    fromDate: "",
  });
}

function removeSegment() {
  if (form.segments.length <= 1) return;
  form.segments.pop();
  form.segments.forEach((segment, index) => {
    segment.segmentOrder = index + 1;
  });
}

function submit() {
  emit("submit", {
    name: form.name.trim(),
    tripType: form.tripType,
    maxPrice: Number(form.maxPrice),
    adultCount: Number(form.adultCount),
    childCount: Number(form.childCount),
    cabinGrade: form.cabinGrade,
    returnDate: form.tripType === "round_trip" ? form.returnDate : null,
    segments: form.segments.map((segment, index) => ({
      segmentOrder: index + 1,
      fromCity: segment.fromCity.trim().toUpperCase(),
      toCity: segment.toCity.trim().toUpperCase(),
      fromDate: segment.fromDate,
    })),
  });
}
</script>

<template>
  <form class="monitor-form panel" @submit.prevent="submit">
    <div class="grid two">
      <label>
        <span>{{ t("monitor.name") }}</span>
        <input v-model="form.name" required />
      </label>
      <label>
        <span>{{ t("monitor.tripType") }}</span>
        <select v-model="form.tripType">
          <option value="one_way">{{ t("monitor.oneWay") }}</option>
          <option value="round_trip">{{ t("monitor.roundTrip") }}</option>
          <option value="multi_segment">{{ t("monitor.openJaw") }}</option>
        </select>
      </label>
    </div>

    <div class="grid three">
      <label>
        <span>{{ t("monitor.maxPrice") }}</span>
        <input v-model.number="form.maxPrice" type="number" min="1" required />
      </label>
      <label>
        <span>{{ t("monitor.adults") }}</span>
        <input v-model.number="form.adultCount" type="number" min="1" />
      </label>
      <label>
        <span>{{ t("monitor.children") }}</span>
        <input v-model.number="form.childCount" type="number" min="0" />
      </label>
    </div>

    <label>
      <span>{{ t("monitor.cabin") }}</span>
      <select v-model="form.cabinGrade">
        <option value="ECONOMY">ECONOMY</option>
        <option value="PREMIUM_ECONOMY">PREMIUM_ECONOMY</option>
        <option value="BUSINESS">BUSINESS</option>
        <option value="FIRST">FIRST</option>
      </select>
    </label>

    <p class="hint">{{ t("monitor.citiesHint") }}</p>

    <div class="segments">
      <article v-for="(segment, index) in form.segments" :key="segment.segmentOrder" class="segment panel">
        <p class="segment-title mono">Segment {{ index + 1 }}</p>
        <div class="grid three">
          <label>
            <span>{{ t("monitor.fromCity") }}</span>
            <input v-model="segment.fromCity" required />
          </label>
          <label>
            <span>{{ t("monitor.toCity") }}</span>
            <input v-model="segment.toCity" required />
          </label>
          <label>
            <span>{{ t("monitor.segmentDate") }}</span>
            <input v-model="segment.fromDate" type="date" required />
          </label>
        </div>
      </article>
    </div>

    <label v-if="form.tripType === 'round_trip'">
      <span>{{ t("monitor.returnDate") }}</span>
      <input v-model="form.returnDate" type="date" required />
    </label>

    <div class="actions">
      <button v-if="canAddSegment" type="button" class="ghost" @click="addSegment">
        {{ t("monitor.addSegment") }}
      </button>
      <button
        v-if="form.tripType !== 'round_trip' && form.segments.length > 1"
        type="button"
        class="ghost"
        @click="removeSegment"
      >
        {{ t("monitor.removeSegment") }}
      </button>
      <button type="submit" class="primary">{{ submitLabel }}</button>
    </div>
  </form>
</template>

<style scoped>
.monitor-form {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.grid {
  display: grid;
  gap: 14px;
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

label {
  display: grid;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 13px;
}

input,
select {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--color-text);
  background: var(--color-bg-muted);
}

.hint {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.segments {
  display: grid;
  gap: 12px;
}

.segment {
  padding: 16px;
}

.segment-title {
  margin: 0 0 12px;
  color: var(--color-accent);
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

button {
  border-radius: 999px;
  padding: 10px 16px;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text);
}

button.primary {
  margin-left: auto;
  background: var(--color-accent);
  border-color: transparent;
  color: white;
}

button.ghost {
  color: var(--color-text-muted);
}

@media (max-width: 760px) {
  .grid.two,
  .grid.three {
    grid-template-columns: 1fr;
  }
}
</style>
