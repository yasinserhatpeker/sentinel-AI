<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{ label: string; values: number[]; unit: string; markers?: number[] }>(), { markers: () => [] });

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
const markerPoints = computed(() => {
  if (!props.values.length) return [];
  const minimum = Math.min(...props.values); const maximum = Math.max(...props.values); const span = maximum - minimum || 1;
  return props.markers.filter((index) => index >= 0 && index < props.values.length).map((index) => ({ x: (index / Math.max(props.values.length - 1, 1)) * 100, y: 52 - ((props.values[index] - minimum) / span) * 42 }));
});
</script>

<template>
  <div class="trend-chart" role="img" :aria-label="`${label}: ${summary} ${unit}`">
    <svg viewBox="0 0 100 60" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0,52 H100" class="baseline" />
      <polyline v-if="chartPoints" :points="chartPoints" class="trend-line" />
      <circle v-for="(point, index) in markerPoints" :key="index" :cx="point.x" :cy="point.y" r="1.8" class="anomaly-marker" />
    </svg>
    <span class="sr-only">{{ label }}: {{ summary }} {{ unit }}</span>
  </div>
</template>
