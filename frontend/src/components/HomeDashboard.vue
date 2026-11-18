<script setup lang="ts">
import type { SystemOverviewResponse } from "../telemetry/types";

type WorkspaceView = "overview" | "service" | "anomalies" | "faults" | "models";

defineProps<{
  overview: SystemOverviewResponse | null;
  loading: boolean;
  error: string;
}>();

const emit = defineEmits<{ navigate: [view: WorkspaceView] }>();

const quickActions: Array<{ view: WorkspaceView; title: string; description: string; meta: string }> = [
  { view: "overview", title: "Sistemin durumunu incele", description: "Tüm servislerin health, latency, queue ve dependency durumunu tek ekranda gör.", meta: "System Overview" },
  { view: "service", title: "Bir servisi analiz et", description: "HTTP, Runtime, Database ve Queue metric’lerini zaman içinde ayrıntılı incele.", meta: "Service Health" },
  { view: "anomalies", title: "Anomaly kayıtlarını aç", description: "Detector kararlarını, score değerlerini ve kararı destekleyen evidence alanlarını gör.", meta: "Anomaly Explorer" },
  { view: "models", title: "Model sonuçlarını karşılaştır", description: "Isolation Forest training score, fault accuracy ve LSTM readiness sonuçlarını değerlendir.", meta: "Model Evaluation" },
];

const workflow = [
  { title: "Telemetry toplanır", description: "Servislerin gerçek HTTP request, process, PostgreSQL ve background job davranışı ölçülür." },
  { title: "Feature window oluşur", description: "Raw metric’ler beş dakikalık zaman pencerelerinde ML için karşılaştırılabilir feature satırlarına dönüştürülür." },
  { title: "Detector karar verir", description: "Static Threshold, Median/MAD ve aktif Isolation Forest her tamamlanmış window’u normal veya anomaly olarak score eder." },
  { title: "Fault ile doğrulanır", description: "Kontrollü high latency, error burst, database slowdown ve queue backlog deneyleri ground truth üretir." },
  { title: "Sonuç ölçülür", description: "Precision, Recall, F1-score, false-positive rate ve detection delay ile detector kalitesi karşılaştırılır." },
];

const glossary = [
  { term: "Telemetry", explanation: "Bir servisin çalışırken ürettiği ölçüm verilerinin genel adıdır. SentinelAI metric ve context alanlarını birlikte kullanır." },
  { term: "Metric", explanation: "Zaman içinde sayısal olarak ölçülen değerdir. Request count, p95 latency, CPU usage ve queue depth birer metric’tir." },
  { term: "p50 / p95 / p99 latency", explanation: "Request sürelerinin percentile değerleridir. p95, request’lerin %95’inin bu sürede veya daha hızlı tamamlandığını gösterir; yavaş kuyruğu görünür kılar." },
  { term: "Error rate", explanation: "Başarısız HTTP request’lerin toplam request sayısına oranıdır. 5xx artışı servis kaynaklı bir problemi işaret edebilir." },
  { term: "Queue depth", explanation: "Worker tarafından henüz işlenmemiş background job sayısıdır. Sürekli yükselmesi tüketimin üretim hızına yetişemediğini gösterebilir." },
  { term: "Anomaly", explanation: "Servisin öğrendiğimiz normal davranışından anlamlı biçimde sapan bir zaman penceresidir. Tek başına kesin incident anlamına gelmez; inceleme sinyalidir." },
  { term: "Isolation Forest", explanation: "Etiketlenmemiş normal telemetry örüntüsünü öğrenen unsupervised anomaly detection modelidir. Nadir ve farklı feature kombinasyonlarını daha kolay izole eder." },
  { term: "Fault Injection", explanation: "Sisteme kontrollü ve süreli bir bozulma uygulanmasıdır. Amaç sistemi rastgele bozmak değil, detector’ların bilinen bir problemi yakalayıp yakalamadığını ölçmektir." },
  { term: "Ground truth", explanation: "Fault’un hangi servis ve zaman penceresinde gerçekten aktif olduğunu belirten doğrulama etiketidir. Accuracy metric’leri bu kayıt üzerinden hesaplanır." },
  { term: "Precision / Recall / F1-score", explanation: "Precision üretilen alarmların ne kadarının doğru olduğunu, Recall gerçek fault’ların ne kadarının yakalandığını, F1-score ise ikisinin dengesini gösterir." },
  { term: "False-positive rate", explanation: "Normal window’ların ne kadarının yanlışlıkla anomaly işaretlendiğini gösterir. Düşük olması gereksiz alarm yorgunluğunu azaltır." },
  { term: "LSTM sequence", explanation: "Ardışık feature window’larından oluşan zaman serisidir. LSTM tek bir noktadan çok davranışın zaman içindeki değişimini değerlendirmek için kullanılır." },
];

const services = [
  ["orders-api", "Sipariş oluşturma ve dependency workflow’un başlangıç noktası."],
  ["payments-api", "Payment authorization ve ödeme background işlerini yürütür."],
  ["inventory-api", "Stok kontrolü, rezervasyon ve database ağırlıklı işlemleri yürütür."],
  ["notifications-api", "Bildirim kayıtlarını ve asenkron teslimat işlerini yönetir."],
  ["reporting-worker", "Rapor işlerini queue üzerinden tüketir ve background processing davranışını üretir."],
];
</script>

<template>
  <div class="home-dashboard">
    <section class="home-hero">
      <div>
        <h2>Genel bakış</h2>
        <p>Servis durumu, anomaly kayıtları, fault deneyleri ve model sonuçlarına bu ekrandan ulaşabilirsiniz.</p>
      </div>
      <button type="button" class="primary-button" @click="emit('navigate', 'overview')">Sistem özetine git</button>
    </section>

    <section aria-labelledby="system-now-title">
      <div class="section-heading">
        <div><h2 id="system-now-title">Servis durumu</h2></div>
        <span v-if="overview">local environment</span>
      </div>
      <p v-if="loading" class="notice" role="status">Canlı sistem özeti yükleniyor…</p>
      <p v-else-if="error" class="notice notice--error" role="alert">Sistem özeti alınamadı: {{ error }}.</p>
      <div v-else class="home-status-grid">
        <article><span>Healthy services</span><strong>{{ overview?.healthy_service_count ?? '—' }}</strong><small>Son aggregate window’a göre normal çalışan servisler</small></article>
        <article><span>Degraded services</span><strong>{{ overview?.degraded_service_count ?? '—' }}</strong><small>Error rate sinyali nedeniyle incelenmesi gereken servisler</small></article>
        <article><span>Highest anomaly score</span><strong>{{ overview?.highest_anomaly_score?.score?.toFixed(3) ?? '—' }}</strong><small>{{ overview?.highest_anomaly_score?.service ?? 'Henüz anomaly kararı yok' }}</small></article>
        <article><span>Fault experiments</span><strong>{{ (overview?.active_fault_count ?? 0) + (overview?.recovering_fault_count ?? 0) }}</strong><small>Aktif veya recovery durumundaki kontrollü deneyler</small></article>
      </div>
    </section>

    <section class="home-section home-section--soft" aria-labelledby="actions-title">
      <div class="section-heading"><div><h2 id="actions-title">İşlemler</h2></div></div>
      <div class="home-action-grid">
        <button v-for="action in quickActions" :key="action.view" type="button" @click="emit('navigate', action.view)">
          <span>{{ action.meta }}</span><strong>{{ action.title }}</strong><p>{{ action.description }}</p><small>İncele →</small>
        </button>
      </div>
    </section>

    <section class="home-section" aria-labelledby="workflow-title">
      <div class="section-heading"><div><h2 id="workflow-title">Telemetry işleme akışı</h2></div></div>
      <ol class="workflow-list">
        <li v-for="(step, index) in workflow" :key="step.title"><span>{{ index + 1 }}</span><div><strong>{{ step.title }}</strong><p>{{ step.description }}</p></div></li>
      </ol>
    </section>

    <section class="home-section home-section--split">
      <div>
        <div class="section-heading"><div><h2>Terimler</h2></div></div>
        <div class="glossary-list">
          <details v-for="item in glossary" :key="item.term"><summary>{{ item.term }}<span aria-hidden="true">+</span></summary><p>{{ item.explanation }}</p></details>
        </div>
      </div>
      <aside class="service-guide">
        <h2>Servisler</h2>
        <dl><div v-for="service in services" :key="service[0]"><dt>{{ service[0] }}</dt><dd>{{ service[1] }}</dd></div></dl>
        <button type="button" class="secondary-button" @click="emit('navigate', 'service')">Service Health ekranını aç</button>
      </aside>
    </section>
  </div>
</template>
