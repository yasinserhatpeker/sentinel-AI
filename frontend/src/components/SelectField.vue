<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

type Option = { label: string; value: string };

const props = withDefaults(defineProps<{
  modelValue: string;
  options: Option[];
  disabled?: boolean;
  placeholder?: string;
}>(), { disabled: false, placeholder: "Seçin" });

const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const open = ref(false);
const root = ref<HTMLElement | null>(null);
const selected = computed(() => props.options.find((option) => option.value === props.modelValue));

function toggle() {
  if (!props.disabled) open.value = !open.value;
}

function choose(value: string) {
  emit("update:modelValue", value);
  open.value = false;
}

function closeOnOutside(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) open.value = false;
}

function closeOnEscape(event: KeyboardEvent) {
  if (event.key === "Escape") open.value = false;
}

onMounted(() => {
  document.addEventListener("mousedown", closeOnOutside);
  document.addEventListener("keydown", closeOnEscape);
});
onBeforeUnmount(() => {
  document.removeEventListener("mousedown", closeOnOutside);
  document.removeEventListener("keydown", closeOnEscape);
});
</script>

<template>
  <div ref="root" class="relative">
    <button class="flex min-h-[46px] w-full items-center justify-between rounded-lg border border-[#bdccc5] bg-white px-3.5 text-left text-sm font-semibold text-[#214037] outline-offset-2 transition focus:border-sentinel-accent focus:ring-3 focus:ring-sentinel-accent/15 focus:outline-none disabled:cursor-not-allowed disabled:bg-[#f0f5f2] disabled:text-[#6b8076]" type="button" :disabled="disabled" :aria-expanded="open" aria-haspopup="listbox" @click="toggle">
      <span>{{ selected?.label ?? placeholder }}</span>
      <svg class="h-4 w-4 text-[#628074] transition-transform" :class="{ 'rotate-180': open }" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="m3.5 6 4.5 4 4.5-4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
    <ul v-if="open" class="absolute z-30 mt-2 max-h-60 w-full overflow-auto rounded-lg border border-[#c8d6cf] bg-white py-1.5 shadow-[0_14px_30px_rgba(9,54,40,.18)]" role="listbox">
      <li v-for="option in options" :key="option.value" role="option" :aria-selected="option.value === modelValue">
        <button class="flex w-full items-center justify-between px-3.5 py-2.5 text-left text-sm font-semibold text-[#29483d] hover:bg-[#eef6f1] focus:bg-[#eef6f1] focus:outline-none" :class="{ 'bg-[#e1f1e9] text-[#126746]': option.value === modelValue }" type="button" @click="choose(option.value)">
          {{ option.label }}
          <span v-if="option.value === modelValue" aria-hidden="true">✓</span>
        </button>
      </li>
    </ul>
  </div>
</template>
