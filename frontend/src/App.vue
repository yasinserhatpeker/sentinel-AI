<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import TrendChart from "./components/TrendChart.vue";
import SelectField from "./components/SelectField.vue";
import HomeDashboard from "./components/HomeDashboard.vue";
import SystemOverview from "./components/SystemOverview.vue";
import LoadingSkeleton from "./components/LoadingSkeleton.vue";
import { dashboardState } from "./telemetry/dashboard-state";
import { getAggregates, getServices, getSystemOverview } from "./telemetry/service";
import type { MetricGroup, SystemOverviewResponse, TelemetryAggregateResponse, TelemetryPoint } from "./telemetry/types";
import { TelemetryApiError } from "./telemetry/types";
import { initialiseCsrf, login, logout, refresh } from "./auth";
import { demoServiceNames, runDemoActivity, runDemoBatch, type DemoOperation, type DemoServiceName } from "./demo-activity";
import { activateModel, createFaultExperiment, getAnomalies, getAnomaly, getEvaluations, getFaultExperiments, getModelReadiness, getModels, repeatFaultExperiment, stopFaultExperiment, trainLstmPrototype, trainModel } from "./analysis/service";
import { activeFaults, percentage, severityLabel } from "./analysis/state";
import type { Anomaly, DetectorEvaluation, DetectorModel, FaultExperiment, LstmPrototypeResult, ModelReadinessResponse } from "./analysis/types";

const token = ref("");
const currentUsername = ref("");
const userMenuOpen = ref(false);
const userMenuRoot = ref<HTMLElement | null>(null);
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
type WorkspaceView = "home" | "overview" | "service" | "anomalies" | "faults" | "models";
const activeView = ref<WorkspaceView>("home");
const analysisLoading = ref(false);
const analysisError = ref("");
const anomalies = ref<Anomaly[]>([]);
const selectedAnomaly = ref<Anomaly | null>(null);
const faultExperiments = ref<FaultExperiment[]>([]);
const models = ref<DetectorModel[]>([]);
const evaluations = ref<DetectorEvaluation[]>([]);
const modelReadiness = ref<ModelReadinessResponse | null>(null);
const lstmResult = ref<LstmPrototypeResult | null>(null);
const isolationForestEvaluations = computed(() => evaluations.value.filter((item) => item.detector_type === "isolation_forest"));
const baselineEvaluations = computed(() => evaluations.value.filter((item) => item.detector_type !== "isolation_forest"));
const faultType = ref("high_latency");
const faultDuration = ref(60);
const faultValue = ref(750);
const navigationItems: Array<{ view: WorkspaceView; label: string; group: "Genel" | "Analiz" }> = [
  { view: "home", label: "Ana sayfa", group: "Genel" },
  { view: "overview", label: "Sistem özeti", group: "Genel" },
  { view: "service", label: "Servis sağlığı", group: "Genel" },
  { view: "anomalies", label: "Anomaly kayıtları", group: "Analiz" },
  { view: "faults", label: "Fault deneyleri", group: "Analiz" },
  { view: "models", label: "Model değerlendirmesi", group: "Analiz" },
];

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

function analysisScope() { return { ...scope(), limit: "200" }; }

function analysisErrorMessage(code: string) {
  return ({
    model_training_insufficient_samples: "Isolation Forest için en az 50 uygun gerçek örnek gerekiyor",
    lstm_minimum_sequences_not_met: "LSTM prototipi için en az 60 geçerli dizi gerekiyor",
    lstm_split_incomplete: "Kronolojik eğitim, doğrulama ve test ayrımları henüz tamamlanmadı",
    validation_failed: "Gönderilen analiz parametreleri geçerli değil",
    request_failed: "Analiz servisine ulaşılamadı",
  } as Record<string, string>)[code] ?? code;
}

function statusLabel(status: string) {
  return ({
    pending: "bekliyor",
    active: "aktif",
    recovering: "toparlanıyor",
    completed: "tamamlandı",
    stopped: "durduruldu",
    failed: "başarısız",
    trained: "eğitildi",
    retired: "kullanımdan kaldırıldı",
    archived: "arşivlendi",
    ready: "hazır",
    collecting: "veri toplanıyor",
    partial: "kısmi veri",
    blocked: "engellendi",
    insufficient_data: "yetersiz veri",
    isolation_forest_ready: "Isolation Forest hazır",
    lstm_ready: "LSTM hazır",
  } as Record<string, string>)[status] ?? status;
}

function faultTypeLabel(type: string) {
  return ({ high_latency: "yüksek gecikme", error_burst: "hata patlaması", database_slowdown: "veritabanı yavaşlaması", queue_backlog: "Queue birikmesi" } as Record<string, string>)[type] ?? type;
}

function values(metric: string, field: keyof TelemetryPoint = "average") {
  return (response.value?.points ?? []).filter((point) => point.metric === metric).map((point) => Number(point[field]));
}

function anomalyMarkerIndexes(metric: string) {
  const anomalyWindows = new Set(anomalies.value.map((item) => new Date(item.window_start).getTime()));
  return (response.value?.points ?? []).filter((point) => point.metric === metric).map((point, index) => {
    const timestamp = new Date(point.timestamp); timestamp.setUTCMinutes(timestamp.getUTCMinutes() - (timestamp.getUTCMinutes() % 5), 0, 0);
    return anomalyWindows.has(timestamp.getTime()) ? index : -1;
  }).filter((index) => index >= 0);
}

function latest(metric: string, field: keyof TelemetryPoint = "average") {
  const series = values(metric, field);
  return series.length ? series.at(-1)?.toFixed(field === "p95" || field === "p99" ? 0 : 1) ?? "—" : "—";
}

function latestWhole(metric: string) {
  const series = values(metric, "last");
  return series.length ? Math.round(series.at(-1) ?? 0).toString() : "—";
}

const queueSourceLabel = computed(() => selectedService.value ? `${selectedService.value} Queue` : "Servis Queue verisi");

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
  if (queueDepth.value === null) return "Bu servis için seçili zaman aralığında Queue Telemetry verisi oluşmadı.";
  if (queueDepth.value > 0) return `${queueDepth.value} iş worker tarafından bekleniyor; worker çalıştıkça bu değer azalır.`;
  if (completedWorkCount.value > 0) return "Bekleyen iş yok. Worker bu zaman aralığında aldığı işleri tamamladı.";
  return "Bekleyen iş yok. Yeni bir kayıt oluşturulduğunda Queue akışı burada görünür.";
});
const queueAgeDescription = computed(() => {
  const age = values("queue.oldest_message_age", "last").at(-1);
  if (age !== undefined) return `En eski gözlemlenen bekleme: ${age.toFixed(1)} saniye.`;
  return "Bekleme yaşı bu servis tarafından henüz ölçülmedi.";
});

async function withFreshAccess<T>(operation: (accessToken: string) => Promise<T>): Promise<T> {
  try {
    return await operation(token.value);
  } catch (error) {
    if (!(error instanceof TelemetryApiError) || error.status !== 401) throw error;
    const session = await refresh();
    token.value = session.access;
    currentUsername.value = session.user.username;
    return operation(token.value);
  }
}

async function loadDashboard() {
  if (!token.value || !selectedService.value) return;
  loading.value = true;
  errorCode.value = "";
  try {
    response.value = await withFreshAccess((accessToken) => getAggregates(accessToken, scope()));
    anomalies.value = (await withFreshAccess((accessToken) => getAnomalies(accessToken, analysisScope()))).results;
  } catch (error) {
    response.value = null;
    errorCode.value = error instanceof TelemetryApiError ? error.code : "request_failed";
  } finally {
    loading.value = false;
  }
}

async function loadAnomalies() {
  if (!selectedService.value) return;
  analysisLoading.value = true; analysisError.value = ""; selectedAnomaly.value = null;
  try { anomalies.value = (await withFreshAccess((accessToken) => getAnomalies(accessToken, analysisScope()))).results; }
  catch (error) { anomalies.value = []; analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; }
  finally { analysisLoading.value = false; }
}
async function openAnomaly(id: string) {
  analysisLoading.value = true;
  try { selectedAnomaly.value = (await withFreshAccess((accessToken) => getAnomaly(accessToken, id))).anomaly; }
  catch (error) { analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; }
  finally { analysisLoading.value = false; }
}
async function loadFaults() {
  if (!selectedService.value) return;
  analysisLoading.value = true; analysisError.value = "";
  try { faultExperiments.value = (await withFreshAccess((accessToken) => getFaultExperiments(accessToken, analysisScope()))).results; }
  catch (error) { faultExperiments.value = []; analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; }
  finally { analysisLoading.value = false; }
}
function faultParameters() {
  return faultType.value === "error_burst" ? { error_probability: Math.min(1, Math.max(0.05, faultValue.value / 100)) } : { delay_ms: faultValue.value };
}
async function createFault() {
  analysisLoading.value = true; analysisError.value = "";
  try {
    await withFreshAccess((accessToken) => createFaultExperiment(accessToken, { environment: "local", service: selectedService.value, fault_type: faultType.value, duration_seconds: faultDuration.value, parameters: faultParameters(), seed: 42 }));
    await loadFaults(); await loadSystemOverview();
  } catch (error) { analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; analysisLoading.value = false; }
}
async function stopFault(id: string) { analysisLoading.value = true; try { await withFreshAccess((accessToken) => stopFaultExperiment(accessToken, id)); await loadFaults(); await loadSystemOverview(); } catch (error) { analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; analysisLoading.value = false; } }
async function repeatFault(id: string) { analysisLoading.value = true; try { await withFreshAccess((accessToken) => repeatFaultExperiment(accessToken, id)); await loadFaults(); } catch (error) { analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; analysisLoading.value = false; } }
async function loadModelsAndEvaluations() {
  if (!selectedService.value) return;
  analysisLoading.value = true; analysisError.value = "";
  try { const [modelResponse, evaluationResponse, readinessResponse] = await Promise.all([withFreshAccess((accessToken) => getModels(accessToken, analysisScope())), withFreshAccess((accessToken) => getEvaluations(accessToken, analysisScope())), withFreshAccess((accessToken) => getModelReadiness(accessToken, analysisScope()))]); models.value = modelResponse.results; evaluations.value = evaluationResponse.results; modelReadiness.value = readinessResponse; }
  catch (error) { models.value = []; evaluations.value = []; modelReadiness.value = null; analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; }
  finally { analysisLoading.value = false; }
}
async function trainIsolationForest() { analysisLoading.value = true; analysisError.value = ""; try { await withFreshAccess((accessToken) => trainModel(accessToken, { ...scope(), minimum_samples: 50, contamination: 0.05, random_state: 42 })); await loadModelsAndEvaluations(); } catch (error) { analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; analysisLoading.value = false; } }
async function activateIsolationForest(id: string) { analysisLoading.value = true; try { await withFreshAccess((accessToken) => activateModel(accessToken, id)); await loadModelsAndEvaluations(); } catch (error) { analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; analysisLoading.value = false; } }
async function runLstmPrototype() { analysisLoading.value = true; analysisError.value = ""; try { lstmResult.value = await withFreshAccess((accessToken) => trainLstmPrototype(accessToken, { ...scope(), minimum_sequences: 60, sequence_length: 12, epochs: 25, seed: 42 })); await loadModelsAndEvaluations(); } catch (error) { lstmResult.value = null; analysisError.value = error instanceof TelemetryApiError ? error.code : "request_failed"; analysisLoading.value = false; } }
async function switchView(view: WorkspaceView) {
  activeView.value = view;
  if (view === "models" && range.value !== "24h") range.value = "24h";
  await nextTick();
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (view === "home" || view === "overview") await loadSystemOverview();
  if (view === "service") await loadDashboard();
  if (view === "anomalies") await loadAnomalies();
  if (view === "faults") await loadFaults();
  if (view === "models") await loadModelsAndEvaluations();
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
    activityMessage.value = `${result.methods} tamamlandı. GET ile ${result.recordCount} kayıt okundu; gösterge paneli güncellendi.`;
  } catch (error) {
    activityMessage.value = error instanceof Error ? `Demo isteği başarısız: ${error.message}` : "Demo isteği başarısız.";
  } finally {
    generatingActivity.value = false;
  }
}

async function runBatchActivity(count: 10 | 100 | 1000) {
  if (!token.value || !selectedService.value || !demoServiceNames.includes(selectedService.value as DemoServiceName)) return;
  generatingActivity.value = true;
  activityMessage.value = `${count} gerçek kayıt ve bunlara bağlı arka plan işleri oluşturuluyor…`;
  try {
    const result = await runDemoBatch(selectedService.value as DemoServiceName, count);
    await new Promise((resolve) => window.setTimeout(resolve, count === 10 ? 1200 : count === 100 ? 2500 : 7000));
    const discovered = await withFreshAccess((accessToken) => getServices(accessToken, "local"));
    services.value = discovered.services;
    await loadDashboard();
    activityMessage.value = `${result.createdCount} kayıt oluşturuldu. ${result.recordCount} kayıt okundu; HTTP ve Queue Telemetry verileri güncellendi.`;
  } catch (error) {
    activityMessage.value = error instanceof Error ? `Toplu kayıt isteği başarısız: ${error.message}` : "Toplu kayıt isteği başarısız.";
  } finally {
    generatingActivity.value = false;
  }
}

function selectService(value: string) {
  selectedService.value = value;
  void switchView(activeView.value);
}

function inspectOverviewService(service: string) {
  selectedService.value = service;
  void switchView("service");
}

function selectRange(value: string) {
  range.value = value as "1h" | "6h" | "24h";
  void switchView(activeView.value);
}

async function continueWithToken() {
  errorCode.value = "";
  loading.value = true;
  try {
    const session = await login(identifier.value, password.value);
    token.value = session.access;
    currentUsername.value = session.user.username;
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
async function restoreSession() { await initialiseCsrf(); try { const session = await refresh(); token.value = session.access; currentUsername.value = session.user.username; const discovered = await getServices(token.value, "local"); services.value = discovered.services; selectedService.value = discovered.services[0] ?? "orders-api"; if (discovered.services.length) await loadDashboard(); await loadSystemOverview(); } catch { token.value = ""; currentUsername.value = ""; } }
function handleUserMenuOutside(event: PointerEvent) {
  if (!userMenuOpen.value) return;
  if (event.target instanceof Node && userMenuRoot.value?.contains(event.target)) return;
  userMenuOpen.value = false;
}

async function signOut() { userMenuOpen.value = false; await logout(); token.value = ""; currentUsername.value = ""; response.value = null; services.value = []; }
onMounted(() => { document.addEventListener("pointerdown", handleUserMenuOutside); void restoreSession(); });
onBeforeUnmount(() => document.removeEventListener("pointerdown", handleUserMenuOutside));
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

  <div v-else class="portal-shell">
    <aside class="portal-sidebar">
      <button type="button" class="portal-brand" aria-label="Ana sayfaya git" @click="switchView('home')">sentinel<span>AI</span></button>
      <nav class="portal-nav" aria-label="Ana navigasyon">
        <template v-for="group in ['Genel', 'Analiz'] as const" :key="group">
          <p>{{ group }}</p>
          <button v-for="item in navigationItems.filter((entry) => entry.group === group)" :key="item.view" :class="{ active: activeView === item.view }" @click="switchView(item.view)">
            {{ item.label }}
          </button>
        </template>
      </nav>
      <div class="portal-sidebar-footer">
        <span>Ortam</span>
        <strong>Yerel</strong>
      </div>
    </aside>
    <section class="portal-stage" id="dashboard">
      <header class="portal-header">
        <div ref="userMenuRoot" class="portal-user-menu">
          <button type="button" class="portal-user-trigger" aria-label="Kullanıcı menüsü" :aria-expanded="userMenuOpen" @click="userMenuOpen = !userMenuOpen">
            <span class="portal-user-avatar" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="3.5"/><path d="M5.5 20c.6-4 3-6 6.5-6s5.9 2 6.5 6"/></svg>
            </span>
            <svg class="portal-user-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
          </button>
          <div v-if="userMenuOpen" class="portal-user-dropdown">
            <div><span>Oturum</span><strong>{{ currentUsername }}</strong></div>
            <button type="button" @click="signOut">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10"/></svg>
              Çıkış yap
            </button>
          </div>
        </div>
      </header>
      <main class="portal-main">
      <div class="dashboard-content">
        <HomeDashboard v-if="activeView === 'home'" :overview="overview" :loading="overviewLoading" :error="overviewError" @navigate="switchView" />
        <SystemOverview v-if="activeView === 'overview'" :overview="overview" :loading="overviewLoading" :error="overviewError" @refresh="loadSystemOverview" @inspect-service="inspectOverviewService" />
        <section v-if="['anomalies','faults','models'].includes(activeView)" class="scope-bar" aria-label="Analiz kapsamı">
          <label>Ortam<span class="static-field">Yerel</span></label>
          <label>Servis<SelectField :model-value="selectedService" :options="serviceOptions" placeholder="Servis seçin" @update:model-value="selectService" /></label>
          <label>Zaman aralığı<SelectField :model-value="range" :options="rangeOptions" @update:model-value="selectRange" /></label>
          <button class="secondary-button" :disabled="analysisLoading" @click="switchView(activeView)">Yenile</button>
        </section>
        <p v-if="analysisError && activeView !== 'service'" class="notice notice--error" role="alert">{{ analysisErrorMessage(analysisError) }}.</p>
        <LoadingSkeleton v-if="analysisLoading && activeView !== 'service'" variant="analysis" />

        <section v-if="activeView === 'anomalies' && !analysisLoading" class="analysis-grid">
          <article class="panel analysis-list"><header><div><p class="eyebrow">ANOMALY KAYITLARI</p><h2>Detector kararları</h2></div><span>{{ anomalies.length }} kayıt</span></header><p v-if="!anomalies.length" class="notice">Seçili kapsam içinde anomaly bulunamadı.</p><button v-for="item in anomalies" :key="item.id" class="record-row" @click="openAnomaly(item.id)"><span><strong>{{ item.service }}</strong><small>{{ new Date(item.window_start).toLocaleString('tr-TR') }} · {{ item.detector_type }}</small></span><span class="status-chip" :class="`status-chip--${item.severity}`">{{ severityLabel(item.severity) }} · {{ item.score?.toFixed(3) ?? '—' }}</span></button></article>
          <article class="panel"><header><div><p class="eyebrow">KANITLAR</p><h2>Anomaly detayı</h2></div><span>{{ selectedAnomaly?.model_version ?? selectedAnomaly?.detector_version ?? '—' }}</span></header><p v-if="!selectedAnomaly" class="notice">Kanıtları görmek için bir anomaly kaydı seçin.</p><template v-else><dl class="detail-list"><div><dt>Detector</dt><dd>{{ selectedAnomaly.detector_type }} · {{ selectedAnomaly.detector_version }}</dd></div><div><dt>Normalize skor / eşik</dt><dd>{{ selectedAnomaly.score?.toFixed(4) ?? '—' }} / {{ selectedAnomaly.threshold?.toFixed(4) ?? '—' }}</dd></div><div><dt>Ham skor / eşik</dt><dd>{{ selectedAnomaly.raw_score?.toFixed(4) ?? '—' }} / {{ selectedAnomaly.raw_threshold?.toFixed(4) ?? '—' }}</dd></div><div><dt>Nedenler</dt><dd>{{ selectedAnomaly.reasons.join(', ') || '—' }}</dd></div></dl><div class="evidence-grid"><div v-for="(value,key) in selectedAnomaly.evidence" :key="key"><span>{{ key }}</span><strong>{{ value ?? '—' }}</strong></div></div></template></article>
        </section>

        <section v-if="activeView === 'faults' && !analysisLoading" class="grid gap-4">
          <p v-if="activeFaults(faultExperiments).length" class="notice notice--warning" role="alert"><strong>Aktif fault:</strong> {{ activeFaults(faultExperiments).map((item) => `${item.service} · ${faultTypeLabel(item.fault_type)} · ${statusLabel(item.status)}`).join(', ') }}</p>
          <article class="panel"><header><div><p class="eyebrow">KONTROLLÜ FAULT</p><h2>Yeni yerel deney</h2></div><span>süper yönetici</span></header><p class="panel-description">Fault yalnızca izinli listedeki yerel demo servisinde, süre ve şiddet sınırlarıyla çalışır.</p><div class="form-grid"><label>Fault türü<select v-model="faultType"><option value="high_latency">Yüksek gecikme</option><option value="error_burst">Hata patlaması</option><option value="database_slowdown">Veritabanı yavaşlaması</option><option value="queue_backlog">Queue birikmesi</option></select></label><label>Süre (sn)<input v-model.number="faultDuration" type="number" min="15" max="600" /></label><label>{{ faultType === 'error_burst' ? 'Hata olasılığı (%)' : 'Gecikme (ms)' }}<input v-model.number="faultValue" type="number" :min="faultType === 'error_burst' ? 5 : 50" :max="faultType === 'error_burst' ? 100 : 5000" /></label><button class="primary-button" :disabled="analysisLoading || Boolean(activeFaults(faultExperiments).length)" @click="createFault">Deneyi başlat</button></div></article>
          <article class="panel"><header><div><p class="eyebrow">DENEY GEÇMİŞİ</p><h2>Fault geçmişi</h2></div><span>{{ faultExperiments.length }} kayıt</span></header><p v-if="!faultExperiments.length" class="notice">Bu kapsam için fault deneyi bulunmuyor.</p><div v-for="item in faultExperiments" :key="item.id" class="table-row"><span><strong>{{ faultTypeLabel(item.fault_type) }}</strong><small>{{ item.service }} · {{ item.duration_seconds }} sn · rastgelelik tohumu {{ item.seed }}</small></span><span class="status-chip">{{ statusLabel(item.status) }}</span><div class="row-actions"><button v-if="['pending','active'].includes(item.status)" @click="stopFault(item.id)">Durdur</button><button v-if="['completed','stopped','failed'].includes(item.status)" @click="repeatFault(item.id)">Tekrarla</button></div></div></article>
        </section>

        <section v-if="activeView === 'models' && !analysisLoading" class="grid gap-4">
          <article class="panel"><header><div><p class="eyebrow">VERİ HAZIRLIĞI</p><h2>Gerçek model verisi</h2></div><span>{{ statusLabel(modelReadiness?.status ?? 'veri yok') }}</span></header><p v-if="!modelReadiness" class="notice">Seçili kapsam için veri hazırlığı bilgisi bulunmuyor.</p><template v-else><p class="panel-description">Bu değerler yalnızca tamamlanmış gerçek `features.v2` pencerelerinden hesaplanır; eksik zamanlar veya yapay kayıtlar hazır sayılmaz.</p><div class="summary-grid !my-4"><article class="metric-card"><p>Feature örnekleri</p><strong>{{ modelReadiness.feature_sample_count }}</strong><span>Isolation Forest için uygun: {{ modelReadiness.eligible_isolation_forest_sample_count }} / {{ modelReadiness.isolation_forest_minimum_samples }}</span></article><article class="metric-card"><p>Kesintisiz window</p><strong>{{ modelReadiness.longest_contiguous_window_count }}</strong><span>dizi boşluğu: {{ modelReadiness.sequence_gap_count }}</span></article><article class="metric-card"><p>LSTM dizileri</p><strong>{{ modelReadiness.candidate_sequence_count }}</strong><span>en az {{ modelReadiness.lstm_minimum_sequences }}</span></article><article class="metric-card"><p>Tahmini kalan süre</p><strong>{{ modelReadiness.estimated_minutes_remaining_for_lstm }} dk</strong><span>{{ modelReadiness.windows_remaining_for_lstm }} tamamlanmış window</span></article></div><p class="notice" :class="{ 'notice--warning': !modelReadiness.isolation_forest_ready }">Isolation Forest: {{ modelReadiness.isolation_forest_ready ? 'hazır' : 'veri toplanıyor' }} · LSTM: {{ modelReadiness.lstm_ready ? 'hazır' : 'veri toplanıyor' }}</p></template></article>
          <article class="panel"><header><div><p class="eyebrow">ISOLATION FOREST</p><h2>Model yaşam döngüsü</h2></div><button class="primary-button" :disabled="!modelReadiness?.isolation_forest_ready" @click="trainIsolationForest">Seçili kapsamla eğit</button></header><p class="panel-description">Eğitim, zaman sıralı normal `features.v2` satırlarını kullanır ve en az 50 örnek gerektirir.</p><p v-if="!modelReadiness?.isolation_forest_ready" class="notice notice--warning">En az 50 uygun normal örnek oluşana kadar eğitim kilitlidir.</p><p v-if="!models.length" class="notice">Bu servis için model bulunmuyor.</p><div v-for="model in models" :key="model.id" class="table-row"><span><strong>{{ model.model_version }}</strong><small>{{ model.sample_count }} örnek · {{ model.feature_count }} feature · {{ model.detector_version }}</small></span><span class="status-chip" :class="{ 'status-chip--normal': model.status === 'active' }">{{ statusLabel(model.status) }}</span><button v-if="model.status === 'trained'" @click="activateIsolationForest(model.id)">Aktif et</button></div></article>
          <article class="panel"><header><div><p class="eyebrow">ÇEVRİMDIŞI LSTM PROTOTİPİ</p><h2>Dizi değerlendirmesi</h2></div><button class="primary-button" :disabled="!modelReadiness?.lstm_ready" @click="runLstmPrototype">Prototipi çalıştır</button></header><p class="panel-description">12 window içeren kronolojik eğitim, doğrulama ve test ayrımı kullanır. Sonuç yalnızca çevrimdışı değerlendirmedir; canlı detector olarak otomatik etkinleştirilmez.</p><p v-if="!modelReadiness?.lstm_ready" class="notice notice--warning">En az 60 geçerli dizi oluşana kadar çalışma kilitlidir.</p><dl v-if="lstmResult" class="detail-list"><div><dt>Veri ayrımı</dt><dd>{{ lstmResult.train_samples }} eğitim · {{ lstmResult.validation_samples }} doğrulama · {{ lstmResult.test_samples }} test</dd></div><div><dt>Doğrulama doğruluğu</dt><dd>{{ percentage(lstmResult.validation_accuracy) }}</dd></div><div><dt>Test doğruluğu</dt><dd>{{ percentage(lstmResult.test_accuracy) }}</dd></div><div><dt>Etkinleştirme</dt><dd>Yok — çevrimdışı prototip</dd></div></dl></article>
          <article class="panel"><header><div><p class="eyebrow">MODEL EĞİTİM SKORLARI</p><h2>Isolation Forest eğitim sonuçları</h2></div><span>{{ models.length }} model</span></header><p class="panel-description">Isolation Forest gözetimsiz çalışır; bu alan doğruluğu değil, eğitim verisindeki aykırı değer oranını ve ham anomaly skoru dağılımını gösterir. Yüksek skor, anomaly davranışına daha yakın bir örneği belirtir.</p><p v-if="!models.length" class="notice">Seçili servis için eğitim sonucu bulunmuyor.</p><div v-for="model in models" :key="`training-${model.id}`" class="evaluation-row"><div><strong>{{ model.model_version }}</strong><small>{{ statusLabel(model.status) }} · {{ new Date(model.trained_from).toLocaleString('tr-TR') }} — {{ new Date(model.trained_until).toLocaleString('tr-TR') }}</small></div><dl v-if="model.configuration.training_diagnostics" class="training-score-grid"><div><dt>Eğitim örneği</dt><dd>{{ model.sample_count }}</dd></div><div><dt>Feature</dt><dd>{{ model.feature_count }}</dd></div><div><dt>Tahmin edilen aykırı değer</dt><dd>{{ model.configuration.training_diagnostics.predicted_anomaly_count }} · {{ percentage(model.configuration.training_diagnostics.predicted_anomaly_rate) }}</dd></div><div><dt>Ortalama skor</dt><dd>{{ model.configuration.training_diagnostics.score_mean.toFixed(4) }}</dd></div><div><dt>p95 skoru</dt><dd>{{ model.configuration.training_diagnostics.score_p95.toFixed(4) }}</dd></div><div><dt>En yüksek skor</dt><dd>{{ model.configuration.training_diagnostics.score_max.toFixed(4) }}</dd></div></dl><p v-else class="notice notice--warning">Bu eski model için eğitim tanıları henüz oluşturulmadı.</p></div></article>
          <article class="panel"><header><div><p class="eyebrow">ISOLATION FOREST DOĞRULUĞU</p><h2>Gerçek fault doğruluk sonuçları</h2></div><span>{{ isolationForestEvaluations.length }} değerlendirme</span></header><p class="panel-description">Bu skorlar yalnızca aktif modelin canlı karar kayıtları ile kontrollü fault ground truth verisi karşılaştırılarak hesaplanır.</p><p v-if="!isolationForestEvaluations.length" class="notice notice--warning">Aktif modelden sonra tamamlanmış ve skorlanmış kontrollü bir fault deneyi bekleniyor.</p><div v-for="item in isolationForestEvaluations" :key="item.id" class="evaluation-row"><div><strong>{{ item.model_version }}</strong><small>{{ item.detector_type }} · {{ item.detector_version }}</small></div><dl><div><dt>Precision</dt><dd>{{ percentage(item.precision) }}</dd></div><div><dt>Recall</dt><dd>{{ percentage(item.recall) }}</dd></div><div><dt>F1-score</dt><dd>{{ percentage(item.f1_score) }}</dd></div><div><dt>Yanlış pozitif oranı</dt><dd>{{ percentage(item.false_positive_rate) }}</dd></div><div><dt>Tespit gecikmesi</dt><dd>{{ item.detection_delay_seconds ?? '—' }} sn</dd></div></dl><p class="confusion-line">Karmaşıklık matrisi · TP {{ item.confusion.true_positive }} · FP {{ item.confusion.false_positive }} · TN {{ item.confusion.true_negative }} · FN {{ item.confusion.false_negative }}</p></div></article>
          <article class="panel"><header><div><p class="eyebrow">BASELINE DEĞERLENDİRMESİ</p><h2>Static Threshold ve Median/MAD</h2></div><span>{{ baselineEvaluations.length }} değerlendirme</span></header><p class="panel-description">Aynı ground truth üzerindeki açıklanabilir baseline sonuçları, Isolation Forest ile karşılaştırma için korunur.</p><p v-if="!baselineEvaluations.length" class="notice">Tamamlanmış deney için baseline değerlendirme sonucu bulunmuyor.</p><div v-for="item in baselineEvaluations" :key="item.id" class="evaluation-row"><div><strong>{{ item.detector_type }} · {{ item.detector_version }}</strong><small>{{ item.configuration_version }}</small></div><dl><div><dt>Precision</dt><dd>{{ percentage(item.precision) }}</dd></div><div><dt>Recall</dt><dd>{{ percentage(item.recall) }}</dd></div><div><dt>F1-score</dt><dd>{{ percentage(item.f1_score) }}</dd></div><div><dt>Yanlış pozitif oranı</dt><dd>{{ percentage(item.false_positive_rate) }}</dd></div><div><dt>Tespit gecikmesi</dt><dd>{{ item.detection_delay_seconds ?? '—' }} sn</dd></div></dl></div></article>
        </section>

        <template v-if="activeView === 'service'">
        <section class="scope-bar" aria-label="Gösterge paneli kapsamı">
          <label>Ortam<span class="static-field">Yerel</span></label>
          <label>Servis<SelectField :model-value="selectedService" :options="serviceOptions" :disabled="!serviceOptions.length" placeholder="Servis seçin" @update:model-value="selectService" /></label>
          <label>Zaman aralığı<SelectField :model-value="range" :options="rangeOptions" @update:model-value="selectRange" /></label>
          <button class="secondary-button" :disabled="loading || !selectedService" @click="loadDashboard">Yenile</button>
        </section>

        <section class="mb-[18px] flex flex-wrap items-center justify-between gap-4 rounded-[14px] border border-[#d6e2dc] bg-[#fbfcfb] px-[22px] py-[18px] shadow-[0_8px_18px_rgba(12,57,43,.06)]" aria-label="Gerçek demo aktivitesi">
          <div>
            <p class="m-0 text-[11px] font-bold tracking-[.08em] text-[#61776d]">CANLI DEMO AKTİVİTESİ</p>
            <h2 class="mt-1 mb-0 text-[17px] tracking-[-.025em] text-[#203c33]">Seçili servis için gerçek API işlemi oluştur</h2>
            <p class="mt-1 mb-0 text-[13px] text-[#657a71]">Her buton gerçek CRUD isteği çalıştırır. Gösterge paneli yalnızca HTTP, ORM ve Queue işlemlerinin ürettiği Telemetry verisini gösterir.</p>
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

        <p v-if="viewState === 'error'" class="notice notice--error" role="alert">Gösterge paneli isteği başarısız: {{ errorCode }}.</p>
        <LoadingSkeleton v-else-if="viewState === 'loading'" variant="service" />
        <p v-else-if="viewState === 'empty-services'" class="notice">Henüz yerel bir servis bulunmuyor. Yerel demo Telemetry verisini üretip tekrar deneyin.</p>
        <template v-else-if="hasData">
          <p v-if="viewState === 'partial'" class="notice notice--warning" role="status">Kısmi veri: {{ partialGroups.join(", ") }} metrikleri bu kapsam için kullanılamıyor.</p>
          <section class="summary-grid" aria-label="Seçili servis özeti">
            <article class="metric-card"><p>İstek sayısı</p><strong>{{ latestSampleCount("http.server.request_count") }}</strong><span>en güncel ölçüm penceresindeki HTTP isteği</span></article>
            <article class="metric-card"><p>Hata oranı</p><strong>{{ latest("http.server.error_rate", "last") }}%</strong><span>HTTP isteklerinin başarısızlık oranı</span></article>
            <article class="metric-card"><p>p95 gecikme</p><strong>{{ latest("http.server.duration", "p95") }} ms</strong><span>isteklerin %95’i bu süreden hızlı</span></article>
            <article class="metric-card"><p>Queue derinliği</p><strong>{{ latestWhole("queue.depth") }}</strong><span>worker tarafından bekleyen gerçek iş sayısı</span></article>
          </section>
          <section class="chart-grid" aria-label="Metrik eğilimleri">
            <article class="panel"><header><div><p class="eyebrow">HTTP</p><h2>Trafik ve gecikme</h2></div><span>p50 / p95 / p99</span></header><p class="panel-description">Gecikme, bir isteğin servis tarafından tamamlanma süresidir. Kırmızı işaretler detector tarafından anomaly olarak işaretlenen feature window’larını gösterir.</p><TrendChart label="HTTP p95 gecikme" :values="values('http.server.duration', 'p95')" :markers="anomalyMarkerIndexes('http.server.duration')" unit="ms" /><dl><div><dt>p50 · medyan</dt><dd>{{ latest("http.server.duration", "p50") }} ms</dd></div><div><dt>p95 · yavaş uç</dt><dd>{{ latest("http.server.duration", "p95") }} ms</dd></div><div><dt>p99 · en kötü uç</dt><dd>{{ latest("http.server.duration", "p99") }} ms</dd></div></dl></article>
            <article class="panel"><header><div><p class="eyebrow">RUNTIME</p><h2>CPU ve bellek</h2></div><span>süreç kullanımı</span></header><p class="panel-description">İşlemci ve bellek değerleri istek işlenirken servis sürecinden ölçülür.</p><TrendChart label="Runtime CPU kullanımı" :values="values('runtime.cpu.usage')" unit="yüzde" /><dl><div><dt>CPU</dt><dd>{{ latest("runtime.cpu.usage") }}%</dd></div><div><dt>Bellek</dt><dd>{{ latest("runtime.memory.usage") }} MB</dd></div></dl></article>
            <article class="panel"><header><div><p class="eyebrow">DATABASE</p><h2>Bağlantılar ve sorgular</h2></div><span>yerel PostgreSQL</span></header><p class="panel-description">Sorgu gecikmesi, ORM’in PostgreSQL sorgusu için harcadığı süreyi; bağlantılar ise açık bağlantı kullanımını gösterir.</p><TrendChart label="Database sorgu gecikmesi" :values="values('db.query.duration', 'p95')" unit="ms" /><dl><div><dt>Bağlantılar</dt><dd>{{ latest("db.connection.usage", "last") }}</dd></div><div><dt>Sorgu p95</dt><dd>{{ latest("db.query.duration", "p95") }} ms</dd></div></dl></article>
            <article class="panel"><header><div><p class="eyebrow">QUEUE</p><h2>Arka plan işleri</h2></div><span>{{ queueSourceLabel }}</span></header><p class="panel-description">{{ queueStateDescription }}</p><TrendChart label="Queue derinliği" :values="values('queue.depth', 'last')" unit="mesaj" /><dl class="queue-metrics"><div><dt>Bekleyen iş</dt><dd>{{ queueDepth ?? "—" }}</dd></div><div><dt>Eklenen iş</dt><dd>{{ queuedWorkCount }}</dd></div><div><dt>Tamamlanan iş</dt><dd>{{ completedWorkCount }}</dd></div><div><dt>Hatalı iş</dt><dd>{{ failedWorkCount }}</dd></div></dl><p class="panel-footnote">{{ queueAgeDescription }}</p></article>
          </section>
        </template>
        <p v-else class="notice">Seçili zaman aralığında toplulaştırılmış Telemetry bulunamadı.</p>
        </template>
      </div>
      </main>
    </section>
  </div>
</template>
