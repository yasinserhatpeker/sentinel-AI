<script setup lang="ts">
import { computed } from "vue";

import type { OverviewFault, OverviewService, SystemOverviewResponse } from "../telemetry/types";
import LoadingSkeleton from "./LoadingSkeleton.vue";

const props = defineProps<{
  overview: SystemOverviewResponse | null;
  loading: boolean;
  error: string;
}>();

const emit = defineEmits<{
  refresh: [];
  inspectService: [service: string];
}>();

const dependencyServices = computed(() => {
  const names = props.overview?.dependencies.flatMap(([source, target]) => [source, target]) ?? [];
  return [...new Set(names)];
});

function number(value: number | null, suffix = "", digits = 0) {
  return value === null ? "—" : `${value.toFixed(digits)}${suffix}`;
}

function statusLabel(status: OverviewService["status"]) {
  return status === "healthy" ? "Sağlıklı" : "İncelenmeli";
}

function severityLabel(severity: NonNullable<OverviewService["anomaly"]>["severity"]) {
  return { normal: "Normal", warning: "Uyarı", critical: "Kritik" }[severity];
}

function faultLabel(fault: OverviewFault | null) {
  if (!fault) return "Yok";
  return ({
    high_latency: "Yüksek gecikme",
    error_burst: "Hata patlaması",
    database_slowdown: "Veritabanı yavaşlaması",
    queue_backlog: "Queue birikmesi",
  } as Record<string, string>)[fault.fault_type] ?? fault.fault_type;
}

function windowLabel(value: string | null) {
  if (!value) return "Son ölçüm yok";
  return `Son ölçüm ${new Date(value).toLocaleString("tr-TR", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}`;
}
</script>

<template>
  <section class="grid gap-4" aria-label="Tüm mikroservislerin sistem özeti">
    <div class="flex flex-wrap items-center justify-between gap-4 border-b border-[#d6e2dc] pb-4">
      <div class="flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px] text-[#60756c]">
        <strong class="text-[16px] text-[#203c33]">{{ overview?.services.length ?? 0 }} servis izleniyor</strong>
        <span><b class="text-[#176f52]">{{ overview?.healthy_service_count ?? 0 }}</b> sağlıklı</span>
        <span><b class="text-[#9a4c3d]">{{ overview?.degraded_service_count ?? 0 }}</b> incelenmeli</span>
        <span><b class="text-[#29483d]">{{ (overview?.active_fault_count ?? 0) + (overview?.recovering_fault_count ?? 0) }}</b> aktif fault</span>
        <span>Yerel ortam</span>
      </div>
      <button class="secondary-button" :disabled="loading" type="button" @click="emit('refresh')">Yenile</button>
    </div>

    <LoadingSkeleton v-if="loading" variant="overview" />
    <p v-else-if="error" class="notice notice--error" role="alert">Sistem özeti alınamadı: {{ error }}.</p>
    <p v-else-if="overview && !overview.services.length" class="notice">Henüz toplulaştırılmış Telemetry verisi bulunmuyor.</p>

    <template v-else-if="overview">
      <div class="grid overflow-hidden rounded-[10px] border border-[#d6e2dc] bg-white md:grid-cols-3 md:divide-x md:divide-[#e0e8e4]">
        <div class="px-5 py-4">
          <span class="block text-[11px] text-[#71847b]">En yavaş p95</span>
          <strong class="mt-1 block text-[20px] text-[#214438]">{{ number(overview.slowest_service?.p95_latency_ms ?? null, ' ms') }}</strong>
          <small class="text-[11px] text-[#82938c]">{{ overview.slowest_service?.service ?? 'Veri yok' }}</small>
        </div>
        <div class="border-t border-[#e0e8e4] px-5 py-4 md:border-t-0">
          <span class="block text-[11px] text-[#71847b]">En yoğun Queue</span>
          <strong class="mt-1 block text-[20px] text-[#214438]">{{ number(overview.busiest_queue?.queue_depth ?? null) }}</strong>
          <small class="text-[11px] text-[#82938c]">{{ overview.busiest_queue?.service ?? 'Veri yok' }}</small>
        </div>
        <div class="border-t border-[#e0e8e4] px-5 py-4 md:border-t-0">
          <span class="block text-[11px] text-[#71847b]">En yüksek anomaly skoru</span>
          <strong class="mt-1 block text-[20px] text-[#214438]">{{ number(overview.highest_anomaly_score?.score ?? null, '', 3) }}</strong>
          <small class="text-[11px] text-[#82938c]">{{ overview.highest_anomaly_score ? `${overview.highest_anomaly_score.service} · ${severityLabel(overview.highest_anomaly_score.severity)}` : 'Anomaly bulunamadı' }}</small>
        </div>
      </div>

      <div class="overflow-hidden rounded-[10px] border border-[#d3dfd9] bg-white shadow-[0_5px_15px_rgba(16,62,47,.035)]">
        <div class="flex flex-wrap items-end justify-between gap-2 border-b border-[#dce6e1] px-5 py-4">
          <div>
            <h2 class="m-0 text-[17px] font-semibold text-[#203c33]">Mikroservisler</h2>
            <p class="mt-1 mb-0 text-[11px] text-[#74877e]">Her satır ilgili metriğin en son tamamlanan gerçek ölçüm penceresini gösterir.</p>
          </div>
          <span class="text-[11px] text-[#81928a]">{{ overview.services.length }} servis</span>
        </div>

        <div class="divide-y divide-[#dce6e1]">
          <article v-for="service in overview.services" :key="service.service" class="px-5 py-5 hover:bg-[#f8faf9]">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="flex flex-wrap items-center gap-3">
                <div><strong class="block text-[14px] text-[#203c33]">{{ service.service }}</strong><small class="mt-1 block text-[10px] text-[#87978f]">{{ windowLabel(service.last_window) }}</small></div>
                <span class="inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold" :class="service.status === 'healthy' ? 'bg-[#e5f3ec] text-[#176f52]' : 'bg-[#faece9] text-[#994638]'">{{ statusLabel(service.status) }}</span>
              </div>
              <button type="button" class="rounded-md border border-[#9eb5aa] bg-white px-3 py-2 text-[10px] font-bold text-[#245b47] hover:border-[#176f52] hover:bg-[#f0f6f2]" @click="emit('inspectService', service.service)">İncele</button>
            </div>

            <div class="mt-4 grid gap-x-5 gap-y-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              <section class="border-t border-[#dbe5e0] pt-2.5" aria-label="HTTP metrikleri">
                <h3 class="m-0 text-[10px] font-bold tracking-[.05em] text-[#60756c]">HTTP</h3>
                <dl class="mt-2 grid grid-cols-3 gap-3 text-[11px]"><div><dt class="text-[#82938c]">İstek</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.request_count) }}</dd></div><div><dt class="text-[#82938c]">Hata</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.error_rate_percent, '%', 1) }}</dd></div><div><dt class="text-[#82938c]">p95</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.p95_latency_ms, ' ms') }}</dd></div></dl>
              </section>
              <section class="border-t border-[#dbe5e0] pt-2.5" aria-label="Runtime metrikleri">
                <h3 class="m-0 text-[10px] font-bold tracking-[.05em] text-[#60756c]">Runtime</h3>
                <dl class="mt-2 grid grid-cols-2 gap-3 text-[11px]"><div><dt class="text-[#82938c]">CPU</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.cpu_percent, '%', 1) }}</dd></div><div><dt class="text-[#82938c]">RAM</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.memory_mb, ' MB', 1) }}</dd></div></dl>
              </section>
              <section class="border-t border-[#dbe5e0] pt-2.5" aria-label="Database metrikleri">
                <h3 class="m-0 text-[10px] font-bold tracking-[.05em] text-[#60756c]">Database</h3>
                <dl class="mt-2 grid grid-cols-2 gap-3 text-[11px]"><div><dt class="text-[#82938c]">Sorgu p95</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.db_query_p95_ms, ' ms') }}</dd></div><div><dt class="text-[#82938c]">Bağlantı</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.db_connections) }}</dd></div></dl>
              </section>
              <section class="border-t border-[#dbe5e0] pt-2.5" aria-label="Queue metrikleri">
                <h3 class="m-0 text-[10px] font-bold tracking-[.05em] text-[#60756c]">Queue</h3>
                <dl class="mt-2 grid grid-cols-3 gap-3 text-[11px]"><div><dt class="text-[#82938c]">Bekleyen</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.queue_depth) }}</dd></div><div><dt class="text-[#82938c]">En eski</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.queue_oldest_age_seconds, ' sn') }}</dd></div><div><dt class="text-[#82938c]">Hatalı</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ number(service.failed_task_count) }}</dd></div></dl>
              </section>
              <section class="border-t border-[#dbe5e0] pt-2.5" aria-label="Analiz sonuçları">
                <h3 class="m-0 text-[10px] font-bold tracking-[.05em] text-[#60756c]">Analiz</h3>
                <dl class="mt-2 grid grid-cols-2 gap-3 text-[11px]"><div><dt class="text-[#82938c]">Anomaly</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ service.anomaly ? `${number(service.anomaly.score, '', 3)} · ${severityLabel(service.anomaly.severity)}` : '—' }}</dd></div><div><dt class="text-[#82938c]">Fault</dt><dd class="mt-1 ml-0 font-bold text-[#29483d]">{{ faultLabel(service.fault) }}</dd></div></dl>
              </section>
            </div>
          </article>
        </div>
      </div>

      <section v-if="dependencyServices.length" class="rounded-[10px] border border-[#d6e2dc] bg-[#f8faf9] px-5 py-4" aria-labelledby="service-flow-title">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div><h2 id="service-flow-title" class="m-0 text-[14px] font-semibold text-[#29483d]">Servis akışı</h2><p class="mt-1 mb-0 text-[10px] text-[#7a8c84]">Siparişten raporlamaya uzanan bağımlılık sırası</p></div>
          <div class="flex flex-wrap items-center gap-2 text-[11px] font-semibold text-[#315749]"><template v-for="(service, index) in dependencyServices" :key="service"><span class="rounded-md border border-[#d2dfd8] bg-white px-3 py-2">{{ service }}</span><span v-if="index < dependencyServices.length - 1" aria-hidden="true" class="text-[#789087]">→</span></template></div>
        </div>
      </section>
    </template>
  </section>
</template>
