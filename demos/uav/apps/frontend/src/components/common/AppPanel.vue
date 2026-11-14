<template>
  <section class="app-panel">
    <header v-if="title || $slots.action" class="app-panel__header">
      <div>
        <h3 v-if="title" class="app-panel__title">{{ title }}</h3>
      </div>
      <div v-if="$slots.action" class="app-panel__action">
        <slot name="action" />
      </div>
    </header>
    <div class="app-panel__body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
}>();
</script>

<style scoped>
.app-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.82);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(14px);
  overflow: auto;
}

.app-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px 12px;
}

.app-panel__title {
  font-size: 15px;
  font-weight: 700;
  color: #f8fafc;
}

.app-panel__description {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #94a3b8;
}

.app-panel__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0 18px 18px;
}
</style>
