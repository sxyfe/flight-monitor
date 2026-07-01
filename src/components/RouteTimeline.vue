<script setup lang="ts">
import { computed } from "vue";
import type { MonitorRule } from "@/types";

const props = defineProps<{
  rule?: MonitorRule | null;
  polling?: boolean;
}>();

const nodes = computed(() => {
  if (!props.rule) return ["BJS", "NRT", "BJS"];
  const cities = [props.rule.segments[0]?.fromCity];
  for (const segment of props.rule.segments) {
    cities.push(segment.toCity);
  }
  return cities.filter(Boolean);
});
</script>

<template>
  <section class="route-panel panel" :class="{ polling }">
    <div class="route-grid" aria-hidden="true" />
    <div class="route-line" />
    <div
      v-for="(city, index) in nodes"
      :key="`${city}-${index}`"
      class="route-node"
      :style="{ left: `${8 + index * (84 / Math.max(nodes.length - 1, 1))}%` }"
    >
      {{ city }}
    </div>
    <slot />
  </section>
</template>

<style scoped>
.route-panel {
  position: relative;
  min-height: 220px;
  overflow: hidden;
  padding: 28px;
}

.route-panel.polling .route-line {
  animation: pulse 1.4s ease-in-out infinite;
}

.route-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--color-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--color-grid) 1px, transparent 1px);
  background-size: 32px 32px;
}

.route-line {
  position: absolute;
  left: 8%;
  right: 8%;
  top: 48%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--color-route), transparent);
}

.route-node {
  position: absolute;
  top: 44%;
  transform: translateX(-50%);
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  font-family: var(--font-mono);
  font-size: 13px;
  animation: node-rise 700ms ease both;
}

@keyframes node-rise {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.55;
  }
  50% {
    opacity: 1;
  }
}
</style>
