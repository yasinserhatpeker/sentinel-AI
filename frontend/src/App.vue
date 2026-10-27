<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import TrendChart from "./components/TrendChart.vue";
import SelectField from "./components/SelectField.vue";
import { dashboardState } from "./telemetry/dashboard-state";
import { getAggregates, getServices, getSystemOverview } from "./telemetry/service";
import type { MetricGroup, SystemOverviewResponse, TelemetryAggregateResponse, TelemetryPoint } from "./telemetry/types";
import { TelemetryApiError } from "./telemetry/types";
import { initialiseCsrf, login, logout, refresh } from "./auth";
import { demoServiceNames, runDemoActivity, runDemoBatch, type DemoOperation, type DemoServiceName } from "./demo-activity";

const token = ref("");
const identifier = ref(""); const password = ref(""); const showPassword = ref(false);
const services = ref<string[]>([]);
const selectedService = ref("");
const range = ref<"1h" | "6h" | "24h">("1h");
const response = ref<TelemetryAggregateResponse | null>(null);
const loading = ref(false);
const errorCode = ref("");
const generatingActivity = ref(false);
const activityMessage = ref("");
const overview = ref<SystemOverviewResponse | null>(null);
const overviewLoading = ref(false);
const overviewError = ref("");

const rangeHours = computed(() => Number.parseInt(range.value, 10));
const hasToken = computed(() => Boolean(token.value));
const hasData = computed(() => Boolean(response.value?.points.length));
const partialGroups = computed(() => {
  if (!response.value) return [] as MetricGroup[];
  return (Object.keys(response.value.availability) as MetricGroup[]).filter((key) => !response.value?.availability[key]);
});
const viewState = computed(() => dashboardState({
  loading: loading.value,
  errorCode: errorCode.value,
  services: services.value,
  response: response.value,
}));
const serviceOptions = computed(() => (services.value.length ? services.value : [...demoServiceNames]).map((service) => ({ label: service, value: service })));
const rangeOptions = [
  { label: "Son 1 saat", value: "1h" },
  { label: "Son 6 saat", value: "6h" },
  { label: "Son 24 saat", value: "24h" },
];

function scope() {
  const end = new Date();
  const start = new Date(end.getTime() - rangeHours.value * 60 * 60 * 1000);
  return { environment: "local" as const, service: selectedService.value, start: start.toISOString(), end: end.toISOString() };
}

function values(metric: string, field: keyof TelemetryPoint = "average") {
  return (response.value?.points ?? []).filter((point) => point.metric === metric).map((point) => Number(point[field]));
}

function latest(metric: string, field: keyof TelemetryPoint = "average") {
  const series = values(metric, field);
  return series.length ? series.at(-1)?.toFixed(field === "p95" || field === "p99" ? 0 : 1) ?? "—" : "—";
}

function latestWhole(metric: string) {
  const series = values(metric, "last");
  return series.length ? Math.round(series.at(-1) ?? 0).toString() : "—";
}

const queueSourceLabel = computed(() => selectedService.value ? `${selectedService.value} queue` : "Service queue");

function latestSampleCount(metric: string) {
  const series = (response.value?.points ?? []).filter((point) => point.metric === metric);
  const latestTimestamp = series.at(-1)?.timestamp;
  if (!latestTimestamp) return "—";
  return series.filter((point) => point.timestamp === latestTimestamp).reduce((total, point) => total + point.count, 0).toString();
}

function metricEventTotal(metric: string) {
  return (response.value?.points ?? [])
    .filter((point) => point.metric === metric)
    .reduce((total, point) => total + point.count, 0);
}

const queueDepth = computed(() => {
  const raw = values("queue.depth", "last").at(-1);
  return raw === undefined ? null : Math.round(raw);
});
const queuedWorkCount = computed(() => metricEventTotal("queue.enqueue_rate"));
const completedWorkCount = computed(() => metricEventTotal("queue.dequeue_rate"));
const failedWorkCount = computed(() => metricEventTotal("queue.failed_task_count"));
const queueStateDescription = computed(() => {
  if (queueDepth.value === null) return "Bu service için seçili zaman aralığında queue telemetry oluşmadı.";
  if (queueDepth.value > 0) return `${queueDepth.value} iş worker tarafından bekleniyor; worker çalıştıkça bu değer azalır.`;
  if (completedWorkCount.value > 0) return "Bekleyen iş yok. Worker bu zaman aralığında aldığı işleri tamamladı.";
  return "Bekleyen iş yok. Yeni bir kayıt oluşturulduğunda queue akışı burada görünür.";
});
const queueAgeDescription = computed(() => {
  const age = values("queue.oldest_message_age", "last").at(-1);
  if (age !== undefined) return `En eski gözlemlenen bekleme: ${age.toFixed(1)} saniye.`;
  return "Bekleme yaşı bu service tarafından henüz ölçülmedi.";
});

async function withFreshAccess<T>(operation: (accessToken: string) => Promise<T>): Promise<T> {
  try {
    return await operation(token.value);
  } catch (error) {
    if (!(error instanceof TelemetryApiError) || error.status !== 401) throw error;
    token.value = await refresh();
    return operation(token.value);
  }
}

async function loadDashboard() {
  if (!token.value || !selectedService.value) return;
  loading.value = true;
  errorCode.value = "";
  try {
    response.value = await withFreshAccess((accessToken) => getAggregates(accessToken, scope()));
  } catch (error) {
    response.value = null;
    errorCode.value = error instanceof TelemetryApiError ? error.code : "request_failed";
  } finally {
    loading.value = false;
  }
}
async function loadSystemOverview() {
  if (!token.value) return;
  overviewLoading.value = true;
  overviewError.value = "";
  try {
    overview.value = await withFreshAccess((accessToken) => getSystemOverview(accessToken));
  } catch (error) {
    overview.value = null;
    overviewError.value = error instanceof TelemetryApiError ? error.code : "request_failed";
  } finally {
    overviewLoading.value = false;
  }
}

const operationLabels: Record<DemoOperation, string> = {
  "create-read": "Kayıt oluştur ve listele",
  update: "Kayıt güncelle",
  delete: "Kayıt sil",
};

async function runRealActivity(operation: DemoOperation) {
  if (!token.value || !selectedService.value || !demoServiceNames.includes(selectedService.value as DemoServiceName)) return;
  generatingActivity.value = true;
  activityMessage.value = `${operationLabels[operation]} işlemi için gerçek API istekleri çalıştırılıyor…`;
  try {
    const result = await runDemoActivity(selectedService.value as DemoServiceName, operation);
    // The demo service publishes in a background-safe bounded request. Give it
    // a moment to reach the core API before reading the live aggregate.
    await new Promise((resolve) => window.setTimeout(resolve, 800));
    const discovered = await withFreshAccess((accessToken) => getServices(accessToken, "local"));
    services.value = discovered.services;
    await loadDashboard();
    activityMessage.value = `${result.methods} tamamlandı. GET ile ${result.recordCount} kayıt okundu; dashboard güncellendi.`;
  } catch (error) {
    activityMessage.value = error instanceof Error ? `Demo isteği başarısız: ${error.message}` : "Demo isteği başarısız.";
  } finally {
    generatingActivity.value = false;
  }
}

async function runBatchActivity(count: 10 | 100 | 1000) {
  if (!token.value || !selectedService.value || !demoServiceNames.includes(selectedService.value as DemoServiceName)) return;
  generatingActivity.value = true;
  activityMessage.value = `${count} gerçek kayıt ve bunlara bağlı background work oluşturuluyor…`;
  try {
    const result = await runDemoBatch(selectedService.value as DemoServiceName, count);
    await new Promise((resolve) => window.setTimeout(resolve, count === 10 ? 1200 : count === 100 ? 2500 : 7000));
    const discovered = await withFreshAccess((accessToken) => getServices(accessToken, "local"));
    services.value = discovered.services;
    await loadDashboard();
    activityMessage.value = `${result.createdCount} kayıt oluşturuldu. ${result.recordCount} kayıt okundu; HTTP ve queue telemetry güncellendi.`;
  } catch (error) {
    activityMessage.value = error instanceof Error ? `Toplu kayıt isteği başarısız: ${error.message}` : "Toplu kayıt isteği başarısız.";
  } finally {
    generatingActivity.value = false;
  }
}

function selectService(value: string) {
  selectedService.value = value;
  void loadDashboard();
}

function selectRange(value: string) {
  range.value = value as "1h" | "6h" | "24h";
  void loadDashboard();
}

async function continueWithToken() {
  errorCode.value = "";
  loading.value = true;
  try {
    token.value = await login(identifier.value, password.value);
    const discovered = await getServices(token.value, "local");
    services.value = discovered.services;
    selectedService.value = discovered.services[0] ?? "orders-api";
    if (discovered.services.length) await loadDashboard();
    await loadSystemOverview();
  } catch (error) {
    token.value = "";
    errorCode.value = error instanceof TelemetryApiError ? error.code : "request_failed";
  } finally {
    loading.value = false;
  }
}
async function restoreSession() { await initialiseCsrf(); try { token.value = await refresh(); const discovered = await getServices(token.value, "local"); services.value = discovered.services; selectedService.value = discovered.services[0] ?? "orders-api"; if (discovered.services.length) await loadDashboard(); await loadSystemOverview(); } catch { token.value = ""; } }
async function signOut() { await logout(); token.value = ""; response.value = null; services.value = []; }
onMounted(() => void restoreSession());
</script>

<template>
  <main v-if="!hasToken" class="grid min-h-screen place-items-center bg-[linear-gradient(118deg,#0d4536_0%,#17634e_48%,#5f8878_100%)] p-6 antialiased">
    <section class="w-full max-w-[550px] rounded-[18px] border-4 border-white/90 bg-[#fbfcfb] px-[46px] pt-[50px] pb-[46px] shadow-[0_20px_48px_rgba(6,33,25,.32)] ring-1 ring-[#d9e3de] max-sm:px-7 max-sm:py-11" aria-labelledby="login-title">
      <div class="text-center text-[40px] leading-none font-extrabold tracking-[-.07em] text-[#125f48]" aria-label="sentinelAI">sentinel<span class="text-sentinel-accent">AI</span></div>
      <h1 id="login-title" class="mt-[46px] mb-[30px] text-[30px] font-medium tracking-[-.045em] text-[#34433d]">Giriş</h1>
      <form class="grid gap-2" @submit.prevent="continueWithToken">
        <label class="grid gap-[7px] text-sm font-semibold text-[#5d6d66]" for="identifier">Kullanıcı adı veya e-posta
          <input id="identifier" v-model="identifier" class="min-h-[52px] w-full rounded-lg border border-[#bdccc5] bg-white px-3.5 text-[15px] text-[#17362d] placeholder:text-[#889b92] outline-offset-2 focus:border-sentinel-accent focus:ring-3 focus:ring-sentinel-accent/15 focus:outline-none" type="text" autocomplete="username" placeholder="Kullanıcı adınızı veya e-posta adresinizi girin" required autofocus />
        </label>
        <label class="grid gap-[7px] text-sm font-semibold text-[#5d6d66]" for="password">Parola</label>
        <div class="relative">
          <input id="password" v-model="password" class="min-h-[52px] w-full rounded-lg border border-[#bdccc5] bg-white py-0 pr-[76px] pl-3.5 text-[15px] text-[#17362d] placeholder:text-[#889b92] outline-offset-2 focus:border-sentinel-accent focus:ring-3 focus:ring-sentinel-accent/15 focus:outline-none" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="Parolanızı girin" required />
          <button class="absolute top-1/2 right-[7px] min-h-[34px] -translate-y-1/2 rounded-md border-0 bg-transparent px-2 text-xs font-bold text-[#39725f]" type="button" :aria-label="showPassword ? 'Parolayı gizle' : 'Parolayı göster'" @click="showPassword = !showPassword">{{ showPassword ? 'Gizle' : 'Göster' }}</button>
        </div>
        <button class="mt-[13px] min-h-[52px] rounded-lg border border-sentinel-primary bg-sentinel-primary px-4 text-[15px] font-semibold text-white transition-colors hover:bg-[#0e5b42] disabled:cursor-wait disabled:opacity-65" :disabled="loading">Giriş yap</button>
      </form>
      <p v-if="errorCode" class="mt-3.5 text-[13px] text-[#85302d]" role="alert">Giriş yapılamadı. Bilgilerinizi kontrol edip tekrar deneyin.</p>
    </section>
  </main>

  <main v-else class="app-shell">
    <section class="workspace" id="dashboard">
      <header class="topbar">
        <div class="topbar-title"><div class="dashboard-brand">sentinel<span>AI</span></div><h1>Servis sağlığı</h1></div><button class="secondary-button" @click="signOut">Çıkış</button>
      </header>
      <div class="dashboard-content">
        <section class="mb-[18px] rounded-[14px] border border-[#d6e2dc] bg-[#fbfcfb] p-5 shadow-[0_8px_18px_rgba(12,57,43,.06)]" aria-label="Sistem özeti">
          <div class="flex items-start justify-between gap-4"><div><p class="eyebrow">SİSTEM ÖZETİ</p><h2 class="mt-1 text-[20px] text-[#203c33]">Yerel sistem sağlığı</h2></div><button class="secondary-button" :disabled="overviewLoading" @click="loadSystemOverview">Yenile</button></div>
          <p v-if="overviewLoading" class="notice mt-4" role="status">Sistem özeti yükleniyor…</p>
          <p v-else-if="overviewError" class="notice notice--error mt-4" role="alert">Sistem özeti isteği başarısız: {{ overviewError }}.</p>
          <p v-else-if="overview && !overview.services.length" class="notice mt-4">Henüz System Overview için aggregate telemetry bulunmuyor.</p>
          <template v-else-if="overview">
            <div class="summary-grid !my-4"><article class="metric-card"><p>Sağlıklı servisler</p><strong>{{ overview.healthy_service_count }}</strong><span>en güncel aggregate telemetry</span></article><article class="metric-card"><p>Sorunlu servisler</p><strong>{{ overview.degraded_service_count }}</strong><span>en güncel error-rate sinyali</span></article><article class="metric-card"><p>En yavaş p95</p><strong>{{ overview.slowest_service?.p95_latency_ms?.toFixed(0) ?? '—' }} ms</strong><span>{{ overview.slowest_service?.service ?? 'veri yok' }}</span></article><article class="metric-card"><p>En yoğun queue</p><strong>{{ overview.busiest_queue?.queue_depth ?? '—' }}</strong><span>{{ overview.busiest_queue?.service ?? 'veri yok' }}</span></article><article class="metric-card"><p>Son fault injection</p><strong>{{ overview.fault_context_available ? 'Mevcut' : '—' }}</strong><span>{{ overview.fault_context_available ? 'en güncel fault context' : 'fault context henüz izlenmiyor' }}</span></article></div>
            <div class="rounded-lg border border-[#e1ebe6] bg-[#f7faf8] px-4 py-3"><p class="m-0 text-[12px] font-semibold text-[#456559]">Dependency zinciri</p><ol class="mt-2 mb-0 flex list-none flex-wrap gap-x-2 gap-y-1 p-0 text-[13px] text-[#315749]"><li v-for="([from, to]) in overview.dependencies" :key="`${from}-${to}`">{{ from }} <span aria-hidden="true">→</span> {{ to }}</li></ol></div>
            <p class="panel-description mt-3">Incident ve anomaly score modülleri henüz uygulanmadığı için bu alanlar kullanılabilir değil.</p>
          </template>
        </section>
        <section class="scope-bar" aria-label="Dashboard scope">
          <label>Ortam<span class="static-field">local</span></label>
          <label>Service<SelectField :model-value="selectedService" :options="serviceOptions" :disabled="!serviceOptions.length" placeholder="Service seçin" @update:model-value="selectService" /></label>
          <label>Zaman aralığı<SelectField :model-value="range" :options="rangeOptions" @update:model-value="selectRange" /></label>
          <button class="secondary-button" :disabled="loading || !selectedService" @click="loadDashboard">Yenile</button>
        </section>

        <section class="mb-[18px] flex flex-wrap items-center justify-between gap-4 rounded-[14px] border border-[#d6e2dc] bg-[#fbfcfb] px-[22px] py-[18px] shadow-[0_8px_18px_rgba(12,57,43,.06)]" aria-label="Gerçek demo aktivitesi">
          <div>
            <p class="m-0 text-[11px] font-bold tracking-[.08em] text-[#61776d]">CANLI DEMO AKTİVİTESİ</p>
            <h2 class="mt-1 mb-0 text-[17px] tracking-[-.025em] text-[#203c33]">Seçili Service için gerçek API işlemi oluştur</h2>
            <p class="mt-1 mb-0 text-[13px] text-[#657a71]">Her buton gerçek CRUD isteği çalıştırır. Dashboard yalnızca HTTP, ORM ve queue işlemlerinin ürettiği telemetry’yi gösterir.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button class="min-h-[40px] rounded-lg border border-sentinel-primary bg-sentinel-primary px-4 text-[13px] font-semibold text-white hover:bg-[#0e5b42] disabled:cursor-wait disabled:opacity-65" :disabled="generatingActivity || !selectedService" @click="runRealActivity('create-read')">{{ generatingActivity ? "İşlem çalışıyor…" : "Kayıt oluştur" }}</button>
            <button class="min-h-[40px] rounded-lg border border-[#7f9b8f] bg-white px-4 text-[13px] font-semibold text-[#245b47] hover:bg-[#f0f6f2] disabled:cursor-wait disabled:opacity-65" :disabled="generatingActivity || !selectedService" @click="runBatchActivity(10)">10 kayıt oluştur</button>
            <button class="min-h-[40px] rounded-lg border border-[#7f9b8f] bg-white px-4 text-[13px] font-semibold text-[#245b47] hover:bg-[#f0f6f2] disabled:cursor-wait disabled:opacity-65" :disabled="generatingActivity || !selectedService" @click="runBatchActivity(100)">100 kayıt oluştur</button>
            <button class="min-h-[40px] rounded-lg border border-[#245b47] bg-[#245b47] px-4 text-[13px] font-semibold text-white hover:bg-[#174836] disabled:cursor-wait disabled:opacity-65" :disabled="generatingActivity || !selectedService" @click="runBatchActivity(1000)">1000 kayıt oluştur</button>
            <button class="min-h-[40px] rounded-lg border border-[#7f9b8f] bg-white px-4 text-[13px] font-semibold text-[#245b47] hover:bg-[#f0f6f2] disabled:cursor-wait disabled:opacity-65" :disabled="generatingActivity || !selectedService" @click="runRealActivity('update')">Güncelle</button>
            <button class="min-h-[40px] rounded-lg border border-[#b86c65] bg-white px-4 text-[13px] font-semibold text-[#963f39] hover:bg-[#fdf3f2] disabled:cursor-wait disabled:opacity-65" :disabled="generatingActivity || !selectedService" @click="runRealActivity('delete')">Sil</button>
          </div>
          <p v-if="activityMessage" class="m-0 w-full border-t border-[#e4ece8] pt-3 text-[13px] text-[#3f6455]" role="status">{{ activityMessage }}</p>
        </section>

        <p v-if="viewState === 'error'" class="notice notice--error" role="alert">Dashboard isteği başarısız: {{ errorCode }}.</p>
        <p v-else-if="viewState === 'loading'" class="notice" role="status">Seçili Telemetry scope yükleniyor…</p>
        <p v-else-if="viewState === 'empty-services'" class="notice">Henüz yerel bir Service bulunmuyor. Yerel demo Telemetry verisini üretip tekrar deneyin.</p>
        <template v-else-if="hasData">
          <p v-if="viewState === 'partial'" class="notice notice--warning" role="status">Kısmi veri: {{ partialGroups.join(", ") }} metrics bu kapsam için kullanılamıyor.</p>
          <section class="summary-grid" aria-label="Selected service summary">
            <article class="metric-card"><p>Request count</p><strong>{{ latestSampleCount("http.server.request_count") }}</strong><span>en güncel ölçüm penceresindeki HTTP request</span></article>
            <article class="metric-card"><p>Error rate</p><strong>{{ latest("http.server.error_rate", "last") }}%</strong><span>HTTP request’lerin başarısızlık oranı</span></article>
            <article class="metric-card"><p>p95 latency</p><strong>{{ latest("http.server.duration", "p95") }} ms</strong><span>request’lerin %95’i bu süreden hızlı</span></article>
            <article class="metric-card"><p>Queue depth</p><strong>{{ latestWhole("queue.depth") }}</strong><span>worker tarafından bekleyen gerçek iş sayısı</span></article>
          </section>
          <section class="chart-grid" aria-label="Metric trends">
            <article class="panel"><header><div><p class="eyebrow">HTTP</p><h2>Traffic ve latency</h2></div><span>p50 / p95 / p99</span></header><p class="panel-description">Latency, bir request’in service tarafından tamamlanma süresidir. Percentile değerleri en yavaş request’leri görünür kılar.</p><TrendChart label="HTTP p95 latency" :values="values('http.server.duration', 'p95')" unit="ms" /><dl><div><dt>p50 · median</dt><dd>{{ latest("http.server.duration", "p50") }} ms</dd></div><div><dt>p95 · slow tail</dt><dd>{{ latest("http.server.duration", "p95") }} ms</dd></div><div><dt>p99 · worst tail</dt><dd>{{ latest("http.server.duration", "p99") }} ms</dd></div></dl></article>
            <article class="panel"><header><div><p class="eyebrow">RUNTIME</p><h2>CPU ve memory</h2></div><span>process utilisation</span></header><p class="panel-description">İşlemci ve bellek değerleri request işlenirken service process’inden ölçülür.</p><TrendChart label="Runtime CPU usage" :values="values('runtime.cpu.usage')" unit="percent" /><dl><div><dt>CPU</dt><dd>{{ latest("runtime.cpu.usage") }}%</dd></div><div><dt>Memory</dt><dd>{{ latest("runtime.memory.usage") }}%</dd></div></dl></article>
            <article class="panel"><header><div><p class="eyebrow">DATABASE</p><h2>Connections ve queries</h2></div><span>yerel PostgreSQL</span></header><p class="panel-description">Query latency, ORM’in PostgreSQL sorgusu için harcadığı süreyi; connections açık bağlantı kullanımını gösterir.</p><TrendChart label="Database query latency" :values="values('db.query.duration', 'p95')" unit="ms" /><dl><div><dt>Connections</dt><dd>{{ latest("db.connection.usage", "last") }}</dd></div><div><dt>Query p95</dt><dd>{{ latest("db.query.duration", "p95") }} ms</dd></div></dl></article>
            <article class="panel"><header><div><p class="eyebrow">QUEUE</p><h2>Background work</h2></div><span>{{ queueSourceLabel }}</span></header><p class="panel-description">{{ queueStateDescription }}</p><TrendChart label="Queue depth" :values="values('queue.depth', 'last')" unit="messages" /><dl class="queue-metrics"><div><dt>Bekleyen iş</dt><dd>{{ queueDepth ?? "—" }}</dd></div><div><dt>Eklenen iş</dt><dd>{{ queuedWorkCount }}</dd></div><div><dt>Tamamlanan iş</dt><dd>{{ completedWorkCount }}</dd></div><div><dt>Hatalı iş</dt><dd>{{ failedWorkCount }}</dd></div></dl><p class="panel-footnote">{{ queueAgeDescription }}</p></article>
          </section>
        </template>
        <p v-else class="notice">Seçili Time range içinde Aggregate Telemetry bulunamadı.</p>
      </div>
    </section>
  </main>
</template>
