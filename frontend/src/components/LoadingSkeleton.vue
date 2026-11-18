<script setup lang="ts">
withDefaults(defineProps<{
  variant?: "home" | "overview" | "analysis" | "service";
}>(), { variant: "analysis" });
</script>

<template>
  <div class="loading-skeleton" :class="`loading-skeleton--${variant}`" role="status" aria-live="polite" aria-busy="true">
    <span class="sr-only">İçerik yükleniyor</span>

    <template v-if="variant === 'home'">
      <div v-for="index in 4" :key="index" class="skeleton-block skeleton-block--status"><i class="skeleton-line skeleton-line--short" /><i class="skeleton-value" /><i class="skeleton-line" /></div>
    </template>

    <template v-else-if="variant === 'overview'">
      <div class="skeleton-summary"><div v-for="index in 3" :key="index"><i class="skeleton-line skeleton-line--short" /><i class="skeleton-value" /><i class="skeleton-line skeleton-line--medium" /></div></div>
      <div class="skeleton-panel skeleton-panel--wide">
        <div class="skeleton-panel-heading"><i class="skeleton-line skeleton-line--medium" /><i class="skeleton-line skeleton-line--short" /></div>
        <div v-for="row in 3" :key="row" class="skeleton-service-row"><div class="skeleton-service-name"><i class="skeleton-line skeleton-line--medium" /><i class="skeleton-line skeleton-line--short" /></div><div v-for="group in 5" :key="group" class="skeleton-service-group"><i class="skeleton-line skeleton-line--short" /><i class="skeleton-line" /><i class="skeleton-line skeleton-line--medium" /></div></div>
      </div>
    </template>

    <template v-else-if="variant === 'service'">
      <div v-for="index in 4" :key="`metric-${index}`" class="skeleton-block skeleton-block--metric"><i class="skeleton-line skeleton-line--short" /><i class="skeleton-value" /><i class="skeleton-line skeleton-line--medium" /></div>
      <div v-for="index in 4" :key="`chart-${index}`" class="skeleton-panel"><div class="skeleton-panel-heading"><i class="skeleton-line skeleton-line--medium" /><i class="skeleton-line skeleton-line--short" /></div><i class="skeleton-chart" /><div class="skeleton-chart-values"><i /><i /><i /></div></div>
    </template>

    <template v-else>
      <div v-for="index in 2" :key="index" class="skeleton-panel"><div class="skeleton-panel-heading"><i class="skeleton-line skeleton-line--medium" /><i class="skeleton-line skeleton-line--short" /></div><div v-for="row in 4" :key="row" class="skeleton-record"><i class="skeleton-line skeleton-line--medium" /><i class="skeleton-line skeleton-line--short" /></div></div>
    </template>
  </div>
</template>
