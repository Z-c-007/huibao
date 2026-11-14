<template>
  <span class="status-badge" :data-tone="tone">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}>();
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: rgba(148, 163, 184, 0.14);
  color: #cbd5e1;
}

.status-badge[data-tone="success"] {
  background: rgba(34, 197, 94, 0.16);
  color: #86efac;
}

.status-badge[data-tone="warning"] {
  background: rgba(245, 158, 11, 0.16);
  color: #fcd34d;
}

.status-badge[data-tone="danger"] {
  background: rgba(248, 113, 113, 0.16);
  color: #fca5a5;
}

.status-badge[data-tone="info"] {
  background: rgba(56, 189, 248, 0.16);
  color: #7dd3fc;
}
</style>
