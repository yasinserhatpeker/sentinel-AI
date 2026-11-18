<script setup lang="ts">
import type { SystemOverviewResponse } from "../telemetry/types";
import LoadingSkeleton from "./LoadingSkeleton.vue";

type WorkspaceView = "overview" | "service" | "anomalies" | "faults" | "models";

defineProps<{
  overview: SystemOverviewResponse | null;
  loading: boolean;
  error: string;
}>();

const emit = defineEmits<{ navigate: [view: WorkspaceView] }>();

const quickActions: Array<{ view: WorkspaceView; title: string; description: string }> = [
  { view: "overview", title: "Sistemin durumunu incele", description: "Tüm servislerin sağlık, gecikme, Queue ve bağımlılık durumunu tek ekranda gör." },
  { view: "service", title: "Bir servisi analiz et", description: "HTTP, Runtime, Database ve Queue metriklerini zaman içinde ayrıntılı incele." },
  { view: "anomalies", title: "Anomaly kayıtlarını aç", description: "Detector kararlarını, skorları ve kararı destekleyen kanıtları gör." },
  { view: "models", title: "Model sonuçlarını karşılaştır", description: "Isolation Forest eğitim skorunu, fault doğruluğunu ve LSTM veri hazırlığını değerlendir." },
];

const workflow = [
  { title: "Telemetry toplanır", description: "Servislerin gerçek HTTP istekleri, süreç, PostgreSQL ve arka plan işi davranışları ölçülür." },
  { title: "Feature window oluşur", description: "Ham metrikler beş dakikalık zaman pencerelerinde ML için karşılaştırılabilir feature satırlarına dönüştürülür." },
  { title: "Detector karar verir", description: "Static Threshold, Median/MAD ve aktif Isolation Forest tamamlanan her window’u normal veya anomaly olarak skorlar." },
  { title: "Fault ile doğrulanır", description: "Kontrollü yüksek gecikme, hata patlaması, veritabanı yavaşlaması ve Queue birikmesi deneyleri ground truth üretir." },
  { title: "Sonuç ölçülür", description: "Precision, Recall, F1-score, yanlış pozitif oranı ve tespit gecikmesiyle detector kalitesi karşılaştırılır." },
];

const frequentlyAskedQuestions = [
  { question: "Bir servisin sağlıklı olup olmadığını nereden görebilirim?", answer: "Sistem özeti tüm servislerin en güncel sağlık durumunu birlikte gösterir. Ayrıntı gerektiğinde Servis sağlığı ekranından HTTP, Runtime, Database ve Queue metriklerini seçili zaman aralığında inceleyebilirsiniz." },
  { question: "Anomaly kaydı oluşması kesin bir arıza olduğu anlamına gelir mi?", answer: "Hayır. Anomaly, servisin öğrenilen normal davranışından anlamlı biçimde saptığını gösteren bir inceleme sinyalidir. Karar vermeden önce skor, kanıtlar, ilgili metrikler ve aktif fault bilgisi birlikte değerlendirilmelidir." },
  { question: "p50, p95 ve p99 gecikme değerleri arasındaki fark nedir?", answer: "p50 tipik istek süresini, p95 yavaş istek grubunu, p99 ise en kötü uç davranışı gösterir. Ortalama normal görünürken p95 veya p99 yükseliyorsa kullanıcıların bir bölümü ciddi yavaşlık yaşıyor olabilir." },
  { question: "Queue derinliği neden sürekli yükselir?", answer: "Queue derinliği, worker tarafından henüz tamamlanmamış arka plan işi sayısıdır. Üretim hızı tüketim hızını geçtiğinde, worker yavaşladığında veya hata aldığında yükselir. En eski mesajın yaşıyla birlikte incelenmelidir." },
  { question: "Fault deneyi çalıştırmak gerçek veriyi bozar mı?", answer: "Fault deneyleri yalnızca yerel demo servislerinde kontrollü ve süreli bozulma üretir. Amaç yüksek gecikme, hata patlaması, veritabanı yavaşlaması veya Queue birikmesi durumlarını tekrarlanabilir biçimde oluşturup detector sonuçlarını ground truth ile karşılaştırmaktır." },
  { question: "Isolation Forest neyi öğrenir?", answer: "Isolation Forest normal kabul edilen Telemetry feature’larının birlikte nasıl davrandığını öğrenir. Nadir görülen ve normal örüntüden uzak feature birleşimlerine daha yüksek anomaly skoru verir." },
  { question: "Precision, Recall ve F1-score nasıl yorumlanır?", answer: "Precision üretilen anomaly uyarılarının ne kadarının doğru olduğunu, Recall gerçek fault’ların ne kadarının yakalandığını gösterir. F1-score bu iki değeri birlikte değerlendirerek detector dengesini özetler." },
  { question: "LSTM sonucu neden hemen oluşmuyor?", answer: "LSTM tek bir metrik noktasını değil, ardışık feature window’larından oluşan zaman dizisini kullanır. Bu nedenle yeterli sayıda kesintisiz ve kronolojik dizi oluşmadan prototip değerlendirmesi başlatılmaz." },
];

const services = [
  ["orders-api", "Sipariş oluşturma ve servis bağımlılığı akışının başlangıç noktası."],
  ["payments-api", "Ödeme yetkilendirmesi ve arka plan ödeme işlerini yürütür."],
  ["inventory-api", "Stok kontrolü, rezervasyon ve Database ağırlıklı işlemleri yürütür."],
  ["notifications-api", "Bildirim kayıtlarını ve asenkron teslimat işlerini yönetir."],
  ["reporting-worker", "Rapor işlerini Queue üzerinden tüketir ve arka plan işleme davranışını üretir."],
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
        <span v-if="overview">yerel ortam</span>
      </div>
      <LoadingSkeleton v-if="loading" variant="home" />
      <p v-else-if="error" class="notice notice--error" role="alert">Sistem özeti alınamadı: {{ error }}.</p>
      <div v-else class="home-status-grid">
        <article><span>Sağlıklı servisler</span><strong>{{ overview?.healthy_service_count ?? '—' }}</strong><small>Son toplulaştırılmış window’a göre normal çalışan servisler</small></article>
        <article><span>Sorunlu servisler</span><strong>{{ overview?.degraded_service_count ?? '—' }}</strong><small>Hata oranı nedeniyle incelenmesi gereken servisler</small></article>
        <article><span>En yüksek anomaly skoru</span><strong>{{ overview?.highest_anomaly_score?.score?.toFixed(3) ?? '—' }}</strong><small>{{ overview?.highest_anomaly_score?.service ?? 'Henüz anomaly kararı yok' }}</small></article>
        <article><span>Fault deneyleri</span><strong>{{ (overview?.active_fault_count ?? 0) + (overview?.recovering_fault_count ?? 0) }}</strong><small>Aktif veya toparlanma durumundaki kontrollü deneyler</small></article>
      </div>
    </section>

    <section class="home-section home-section--soft" aria-labelledby="actions-title">
      <div class="section-heading"><div><h2 id="actions-title">İşlemler</h2></div></div>
      <div class="home-action-grid">
        <button v-for="action in quickActions" :key="action.view" type="button" @click="emit('navigate', action.view)">
          <strong>{{ action.title }}</strong><p>{{ action.description }}</p><small>İncele →</small>
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
        <div class="section-heading"><div><h2>Sıkça sorulan sorular</h2></div></div>
        <div class="faq-list">
          <details v-for="item in frequentlyAskedQuestions" :key="item.question"><summary>{{ item.question }}<span aria-hidden="true">+</span></summary><p>{{ item.answer }}</p></details>
        </div>
      </div>
      <aside class="service-guide">
        <h2>Servisler</h2>
        <dl><div v-for="service in services" :key="service[0]"><dt>{{ service[0] }}</dt><dd>{{ service[1] }}</dd></div></dl>
        <button type="button" class="secondary-button" @click="emit('navigate', 'service')">Servis sağlığı ekranını aç</button>
      </aside>
    </section>
  </div>
</template>
