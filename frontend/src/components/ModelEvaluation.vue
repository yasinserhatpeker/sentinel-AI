<script setup lang="ts">
import { computed } from "vue";

import type { DetectorEvaluation, DetectorModel, LstmPrototypeResult, ModelReadinessResponse } from "../analysis/types";

const props = defineProps<{
  models: DetectorModel[];
  evaluations: DetectorEvaluation[];
  readiness: ModelReadinessResponse | null;
  lstmResult: LstmPrototypeResult | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  trainModel: [];
  activateModel: [modelId: string];
  runLstm: [];
}>();

type EvaluationSummary = {
  count: number;
  precision: number;
  recall: number;
  f1: number;
  falsePositiveRate: number;
  detectionDelay: number | null;
  truePositive: number;
  falsePositive: number;
  trueNegative: number;
  falseNegative: number;
};

function percentage(value: number) {
  return `${(value * 100).toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
}

function detectorName(type: string) {
  return ({ static_threshold: "Static Threshold", median_mad: "Median/MAD", isolation_forest: "Isolation Forest" } as Record<string, string>)[type] ?? type;
}

function summarize(items: DetectorEvaluation[]): EvaluationSummary | null {
  if (!items.length) return null;
  const totals = items.reduce((result, item) => ({
    truePositive: result.truePositive + item.confusion.true_positive,
    falsePositive: result.falsePositive + item.confusion.false_positive,
    trueNegative: result.trueNegative + item.confusion.true_negative,
    falseNegative: result.falseNegative + item.confusion.false_negative,
  }), { truePositive: 0, falsePositive: 0, trueNegative: 0, falseNegative: 0 });
  const precisionDenominator = totals.truePositive + totals.falsePositive;
  const recallDenominator = totals.truePositive + totals.falseNegative;
  const falsePositiveDenominator = totals.falsePositive + totals.trueNegative;
  const precision = precisionDenominator ? totals.truePositive / precisionDenominator : 0;
  const recall = recallDenominator ? totals.truePositive / recallDenominator : 0;
  const delays = items.flatMap((item) => item.detection_delay_seconds === null ? [] : [item.detection_delay_seconds]);
  return {
    count: items.length,
    precision,
    recall,
    f1: precision + recall ? (2 * precision * recall) / (precision + recall) : 0,
    falsePositiveRate: falsePositiveDenominator ? totals.falsePositive / falsePositiveDenominator : 0,
    detectionDelay: delays.length ? delays.reduce((sum, value) => sum + value, 0) / delays.length : null,
    ...totals,
  };
}

const sortedModels = computed(() => [...props.models].sort((left, right) => {
  if (left.status === "active") return -1;
  if (right.status === "active") return 1;
  return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
}));
const activeModel = computed(() => sortedModels.value.find((model) => model.status === "active") ?? null);
const isolationForestEvaluations = computed(() => {
  const all = props.evaluations.filter((item) => item.detector_type === "isolation_forest");
  if (!activeModel.value) return all;
  const active = all.filter((item) => item.model_version === activeModel.value?.model_version);
  return active.length ? active : all;
});
const isolationForestSummary = computed(() => summarize(isolationForestEvaluations.value));
const baselineGroups = computed(() => ["static_threshold", "median_mad"].map((type) => {
  const items = props.evaluations.filter((item) => item.detector_type === type);
  return { type, items, summary: summarize(items) };
}).filter((group) => group.summary));
const lstmProgress = computed(() => {
  if (!props.readiness) return 0;
  return Math.min(100, (props.readiness.candidate_sequence_count / props.readiness.lstm_minimum_sequences) * 100);
});
const isolationProgress = computed(() => {
  if (!props.readiness) return 0;
  return Math.min(100, (props.readiness.eligible_isolation_forest_sample_count / props.readiness.isolation_forest_minimum_samples) * 100);
});

function modelName(model: DetectorModel, index: number) {
  if (model.status === "active") return "Aktif model";
  if (model.status === "trained") return "Aktivasyon bekleyen model";
  return `Önceki model ${index}`;
}

function modelStatus(model: DetectorModel) {
  return ({ active: "Canlı kullanımda", trained: "Aktivasyon bekliyor", retired: "Kullanımdan kaldırıldı", archived: "Arşivlendi" } as Record<string, string>)[model.status] ?? model.status;
}
</script>

<template>
  <div class="model-workspace" :aria-busy="loading">
    <section class="model-panel readiness-panel">
      <div class="section-title">
        <div>
          <h2>Model hazırlığı</h2>
          <p>Gerçek servis ölçümlerinin model eğitimi için yeterli olup olmadığını buradan takip edebilirsiniz.</p>
        </div>
        <span v-if="readiness" class="state-chip" :class="{ ready: readiness.isolation_forest_ready }">
          {{ readiness.isolation_forest_ready ? "Isolation Forest hazır" : "Veri toplanıyor" }}
        </span>
      </div>

      <p v-if="!readiness" class="empty-message">Seçili servis için henüz model verisi bulunmuyor.</p>
      <div v-else class="readiness-grid">
        <article>
          <div class="progress-heading"><strong>Isolation Forest</strong><span>{{ readiness.eligible_isolation_forest_sample_count }} / {{ readiness.isolation_forest_minimum_samples }} örnek</span></div>
          <div class="progress-track"><span :style="{ width: `${isolationProgress}%` }"></span></div>
          <p>{{ readiness.isolation_forest_ready ? "Model eğitimi için yeterli veri var." : "Normal çalışma örnekleri toplanıyor." }}</p>
        </article>
        <article>
          <div class="progress-heading"><strong>LSTM</strong><span>{{ readiness.candidate_sequence_count }} / {{ readiness.lstm_minimum_sequences }} dizi</span></div>
          <div class="progress-track"><span :style="{ width: `${lstmProgress}%` }"></span></div>
          <p v-if="readiness.lstm_ready">Zaman dizisi değerlendirmesi çalıştırılabilir.</p>
          <p v-else>Yaklaşık {{ readiness.estimated_minutes_remaining_for_lstm }} dakika ve {{ readiness.windows_remaining_for_lstm }} ölçüm dönemi kaldı.</p>
        </article>
      </div>
    </section>

    <section class="model-panel">
      <div class="section-title">
        <div>
          <h2>Isolation Forest</h2>
          <p>Normal servis davranışını öğrenir ve bu davranıştan uzaklaşan ölçüm dönemlerini işaretler.</p>
        </div>
        <button class="primary-action" :disabled="loading || !readiness?.isolation_forest_ready" @click="emit('trainModel')">Yeni model eğit</button>
      </div>

      <p v-if="!readiness?.isolation_forest_ready" class="inline-message warning">Eğitim için en az {{ readiness?.isolation_forest_minimum_samples ?? 50 }} uygun örnek gerekir.</p>
      <p v-if="!sortedModels.length" class="empty-message">Bu servis için eğitilmiş model bulunmuyor.</p>
      <div v-else class="model-list">
        <article v-for="(model, index) in sortedModels" :key="model.id" class="model-row">
          <div class="model-row-title">
            <div><h3>{{ modelName(model, index + 1) }}</h3><p>{{ model.sample_count }} eğitim örneği · {{ model.feature_count }} ölçüm özelliği</p></div>
            <span class="state-chip" :class="{ ready: model.status === 'active' }">{{ modelStatus(model) }}</span>
          </div>
          <div class="model-row-meta">
            <span><small>Eğitim aralığı</small>{{ formatDate(model.trained_from) }} – {{ formatDate(model.trained_until) }}</span>
            <button v-if="model.status === 'trained'" class="secondary-action" :disabled="loading" @click="emit('activateModel', model.id)">Canlı kullanıma al</button>
          </div>
          <details v-if="model.configuration.training_diagnostics" class="detail-disclosure">
            <summary>Eğitim ayrıntılarını göster</summary>
            <dl class="training-metrics">
              <div><dt>Sıra dışı bulunan</dt><dd>{{ model.configuration.training_diagnostics.predicted_anomaly_count }} ({{ percentage(model.configuration.training_diagnostics.predicted_anomaly_rate) }})</dd></div>
              <div><dt>Ortalama skor</dt><dd>{{ model.configuration.training_diagnostics.score_mean.toFixed(4) }}</dd></div>
              <div><dt>p95 skoru</dt><dd>{{ model.configuration.training_diagnostics.score_p95.toFixed(4) }}</dd></div>
              <div><dt>En yüksek skor</dt><dd>{{ model.configuration.training_diagnostics.score_max.toFixed(4) }}</dd></div>
            </dl>
            <p class="detail-note">Skor yükseldikçe ölçüm dönemi öğrenilen normal davranıştan daha uzaktır.</p>
          </details>
        </article>
      </div>
    </section>

    <section class="model-panel">
      <div class="section-title">
        <div>
          <h2>LSTM zaman dizisi değerlendirmesi</h2>
          <p>Art arda gelen 12 ölçüm dönemini birlikte değerlendirir. Sonuç yalnızca karşılaştırma amaçlıdır ve canlı anomaly tespitini değiştirmez.</p>
        </div>
        <button class="primary-action" :disabled="loading || !readiness?.lstm_ready" @click="emit('runLstm')">Değerlendirmeyi çalıştır</button>
      </div>
      <p v-if="!readiness?.lstm_ready" class="inline-message warning">En az {{ readiness?.lstm_minimum_sequences ?? 60 }} geçerli zaman dizisi gerekir. Şu anda {{ readiness?.candidate_sequence_count ?? 0 }} dizi hazır.</p>
      <dl v-if="lstmResult" class="result-grid">
        <div><dt>Eğitim verisi</dt><dd>{{ lstmResult.train_samples }} dizi</dd></div>
        <div><dt>Doğrulama verisi</dt><dd>{{ lstmResult.validation_samples }} dizi</dd></div>
        <div><dt>Test verisi</dt><dd>{{ lstmResult.test_samples }} dizi</dd></div>
        <div><dt>Doğrulama doğruluğu</dt><dd>{{ percentage(lstmResult.validation_accuracy) }}</dd></div>
        <div><dt>Test doğruluğu</dt><dd>{{ percentage(lstmResult.test_accuracy) }}</dd></div>
      </dl>
    </section>

    <section class="model-panel">
      <div class="section-title">
        <div>
          <h2>Fault deneyleriyle doğrulama</h2>
          <p>Modelin kontrollü servis sorunlarını ne kadar doğru ve hızlı yakaladığını gösterir.</p>
        </div>
        <span>{{ isolationForestSummary?.count ?? 0 }} deney</span>
      </div>

      <p v-if="!isolationForestSummary" class="inline-message warning">Aktif modelden sonra tamamlanmış ve skorlanmış bir fault deneyi henüz bulunmuyor.</p>
      <template v-else>
        <div class="result-callout" :class="{ strong: isolationForestSummary.f1 >= 0.8 }">
          <strong>{{ isolationForestSummary.f1 >= 0.8 ? "Güçlü sonuç" : isolationForestSummary.f1 >= 0.5 ? "Geliştirilebilir sonuç" : "Daha fazla doğrulama gerekli" }}</strong>
          <span>F1-score {{ percentage(isolationForestSummary.f1) }}</span>
        </div>
        <dl class="result-grid five-columns">
          <div><dt>Precision <span>Alarmların doğruluğu</span></dt><dd>{{ percentage(isolationForestSummary.precision) }}</dd></div>
          <div><dt>Recall <span>Yakalanan gerçek sorunlar</span></dt><dd>{{ percentage(isolationForestSummary.recall) }}</dd></div>
          <div><dt>F1-score <span>Precision ve Recall dengesi</span></dt><dd>{{ percentage(isolationForestSummary.f1) }}</dd></div>
          <div><dt>Yanlış alarm <span>Düşük olması beklenir</span></dt><dd>{{ percentage(isolationForestSummary.falsePositiveRate) }}</dd></div>
          <div><dt>Tespit süresi <span>Düşük olması beklenir</span></dt><dd>{{ isolationForestSummary.detectionDelay === null ? "Ölçülmedi" : `${isolationForestSummary.detectionDelay.toFixed(1)} sn` }}</dd></div>
        </dl>
        <p class="decision-counts">{{ isolationForestSummary.truePositive }} sorun doğru yakalandı · {{ isolationForestSummary.falseNegative }} sorun kaçırıldı · {{ isolationForestSummary.falsePositive }} yanlış alarm oluştu · {{ isolationForestSummary.trueNegative }} normal dönem doğru değerlendirildi</p>

        <details class="detail-disclosure experiment-details">
          <summary>Deney sonuçlarını tek tek göster</summary>
          <div v-for="(item, index) in isolationForestEvaluations" :key="item.id" class="experiment-row">
            <span><strong>Deney {{ index + 1 }}</strong><small>{{ formatDate(item.evaluated_at) }}</small></span>
            <span>Precision {{ percentage(item.precision) }}</span><span>Recall {{ percentage(item.recall) }}</span><span>F1 {{ percentage(item.f1_score) }}</span>
          </div>
        </details>
      </template>
    </section>

    <section class="model-panel">
      <div class="section-title">
        <div>
          <h2>Kural tabanlı yöntemlerle karşılaştırma</h2>
          <p>Static Threshold ve Median/MAD aynı fault deneyleri üzerinde ölçülür. Böylece hangi yöntemin daha güvenilir olduğu görülebilir.</p>
        </div>
      </div>
      <p v-if="!baselineGroups.length" class="empty-message">Karşılaştırma için tamamlanmış fault deneyi bulunmuyor.</p>
      <div v-else class="comparison-list">
        <article v-for="group in baselineGroups" :key="group.type">
          <div class="comparison-title"><h3>{{ detectorName(group.type) }}</h3><span>{{ group.summary?.count }} deney</span></div>
          <dl v-if="group.summary" class="result-grid five-columns compact">
            <div><dt>Precision</dt><dd>{{ percentage(group.summary.precision) }}</dd></div>
            <div><dt>Recall</dt><dd>{{ percentage(group.summary.recall) }}</dd></div>
            <div><dt>F1-score</dt><dd>{{ percentage(group.summary.f1) }}</dd></div>
            <div><dt>Yanlış alarm</dt><dd>{{ percentage(group.summary.falsePositiveRate) }}</dd></div>
            <div><dt>Tespit süresi</dt><dd>{{ group.summary.detectionDelay === null ? "Ölçülmedi" : `${group.summary.detectionDelay.toFixed(1)} sn` }}</dd></div>
          </dl>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.model-workspace { display: grid; gap: 16px; }
.model-panel { min-height: 0; border: 1px solid #d6e2dc; border-radius: 14px; background: #fbfcfb; padding: 24px; box-shadow: 0 8px 18px rgba(12, 57, 43, .055); }
.section-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.section-title h2 { margin: 0; color: #203c33; font-size: 19px; letter-spacing: -.025em; }
.section-title p { max-width: 820px; margin: 8px 0 0; color: #496359; font-size: 13px; line-height: 1.6; }
.section-title > span { color: #60766d; font-size: 12px; white-space: nowrap; }
.primary-action, .secondary-action { flex: 0 0 auto; min-height: 40px; border: 1px solid #146d50; border-radius: 8px; background: #146d50; padding: 0 15px; color: #fff; font-size: 12px; font-weight: 700; }
.secondary-action { background: #fff; color: #146d50; }
button:disabled { cursor: wait; opacity: .55; }
.state-chip { display: inline-flex; min-height: 27px; align-items: center; border-radius: 999px; background: #eef2f0; padding: 0 10px; color: #536c62; font-size: 11px; font-weight: 700; white-space: nowrap; }
.state-chip.ready { background: #e3f3eb; color: #176044; }
.readiness-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }
.readiness-grid article { border: 1px solid #dce7e2; border-radius: 10px; background: #f7faf8; padding: 16px; }
.progress-heading { display: flex; justify-content: space-between; gap: 18px; color: #24493c; font-size: 13px; }
.progress-heading span { color: #587067; font-size: 12px; }
.progress-track { height: 7px; overflow: hidden; margin-top: 12px; border-radius: 999px; background: #e2eae6; }
.progress-track span { display: block; height: 100%; border-radius: inherit; background: #2b8062; }
.readiness-grid p { margin: 10px 0 0; color: #536b61; font-size: 12px; line-height: 1.5; }
.inline-message, .empty-message { margin: 18px 0 0; border: 1px solid #dce7e2; border-radius: 8px; background: #f5f8f6; padding: 13px 15px; color: #426056; font-size: 12px; line-height: 1.55; }
.inline-message.warning { border-color: #ead8b9; background: #fff8ec; color: #70521d; }
.model-list { margin-top: 18px; border-top: 1px solid #dfe8e4; }
.model-row { padding: 18px 0; border-bottom: 1px solid #dfe8e4; }
.model-row:last-child { border-bottom: 0; padding-bottom: 0; }
.model-row-title, .model-row-meta { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.model-row-title h3, .comparison-title h3 { margin: 0; color: #214438; font-size: 15px; }
.model-row-title p { margin: 5px 0 0; color: #60766d; font-size: 12px; }
.model-row-meta { margin-top: 12px; }
.model-row-meta > span { display: grid; gap: 3px; color: #3f5c51; font-size: 12px; }
.model-row-meta small { color: #71857c; font-size: 10px; }
.detail-disclosure { margin-top: 14px; border: 1px solid #dde7e2; border-radius: 8px; background: #f8faf9; }
.detail-disclosure summary { cursor: pointer; padding: 12px 14px; color: #315b4c; font-size: 12px; font-weight: 700; }
.training-metrics, .result-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0; margin: 0; border-top: 1px solid #e0e8e4; padding: 0; }
.training-metrics div, .result-grid div { padding: 14px; }
.training-metrics dt, .result-grid dt { color: #61766d; font-size: 11px; }
.training-metrics dd, .result-grid dd { margin: 5px 0 0; color: #214037; font-size: 16px; font-weight: 740; }
.detail-note { margin: 0; border-top: 1px solid #e0e8e4; padding: 11px 14px; color: #60766d; font-size: 11px; }
.result-grid { margin-top: 18px; border: 1px solid #dce7e2; border-radius: 9px; background: #f8faf9; }
.result-grid.five-columns { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.result-grid dt span { display: block; margin-top: 4px; color: #7a8d85; font-size: 9px; font-weight: 500; line-height: 1.35; }
.result-callout { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 18px; border-left: 4px solid #b8781e; border-radius: 0 8px 8px 0; background: #fff8eb; padding: 12px 15px; color: #6f5017; }
.result-callout.strong { border-color: #2d8766; background: #f0f8f4; color: #236047; }
.result-callout strong { font-size: 13px; }
.result-callout span { font-size: 12px; }
.decision-counts { margin: 12px 0 0; color: #526a60; font-size: 12px; line-height: 1.55; }
.experiment-details { margin-top: 16px; }
.experiment-row { display: grid; grid-template-columns: minmax(150px, 1fr) repeat(3, auto); align-items: center; gap: 18px; border-top: 1px solid #e1e9e5; padding: 12px 14px; color: #476157; font-size: 11px; }
.experiment-row > span:first-child { display: grid; gap: 3px; }
.experiment-row strong { color: #23463a; font-size: 12px; }
.experiment-row small { color: #71857c; font-size: 10px; }
.comparison-list { display: grid; gap: 14px; margin-top: 18px; }
.comparison-list > article { border: 1px solid #dce7e2; border-radius: 9px; overflow: hidden; }
.comparison-title { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px; }
.comparison-title span { color: #667c72; font-size: 11px; }
.result-grid.compact { margin: 0; border: 0; border-top: 1px solid #e0e8e4; border-radius: 0; }

@media (max-width: 900px) {
  .result-grid.five-columns { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .training-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 650px) {
  .model-panel { padding: 18px; }
  .section-title, .model-row-title, .model-row-meta { align-items: stretch; flex-direction: column; }
  .section-title button, .model-row-meta button { width: 100%; }
  .readiness-grid, .result-grid.five-columns, .training-metrics, .result-grid { grid-template-columns: 1fr; }
  .experiment-row { grid-template-columns: 1fr 1fr; }
}
</style>
