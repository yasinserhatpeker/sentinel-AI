<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ label: string; values: number[]; unit: string }>();

const chartPoints = computed(() => {
  if (!props.values.length) return "";
  const minimum = Math.min(...props.values);
  const maximum = Math.max(...props.values);
  const span = maximum - minimum || 1;
  return props.values
    .map((value, index) => `${(index / Math.max(props.values.length - 1, 1)) * 100},${52 - ((value - minimum) / span) * 42}`)
    .join(" ");
});

const summary = computed(() => (props.values.length ? props.values.at(-1)?.toFixed(1) : "No data"));
</script>

<template>
  <div class="trend-chart" role="img" :aria-label="`${label}: ${summary} ${unit}`">
    <svg viewBox="0 0 100 60" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0,52 H100" class="baseline" />
      <polyline v-if="chartPoints" :points="chartPoints" class="trend-line" />
    </svg>
    <span class="sr-only">{{ label }}: {{ summary }} {{ unit }}</span>
  </div>
</template>
