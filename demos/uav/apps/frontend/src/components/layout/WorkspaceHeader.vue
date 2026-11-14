<template>
  <header class="workspace-header">
    <div>
      <!-- <p class="workspace-header__eyebrow">{{ environmentLabel }}</p> -->
      <h1 class="workspace-header__title">{{ title }}</h1>
      <!-- <p class="workspace-header__subtitle">{{ subtitle }}</p> -->
    </div>
    <div class="workspace-header__meta">
      <div
        v-for="item in stats"
        :key="item.label"
        class="workspace-header__stat"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
interface HeaderStat {
  label: string;
  value: string;
}

defineProps<{
  title: string;
  // subtitle: string;
  // environmentLabel: string;
  stats: HeaderStat[];
}>();
</script>

<style scoped>
.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.workspace-header__eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #7dd3fc;
}

.workspace-header__title {
  margin-top: 4px;
  font-size: 28px;
  line-height: 1.1;
  color: #f8fafc;
}

.workspace-header__subtitle {
  margin-top: 8px;
  max-width: 720px;
  font-size: 13px;
  line-height: 1.6;
  color: #94a3b8;
}

.workspace-header__meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(96px, 1fr));
  gap: 12px;
  min-width: 320px;
}

.workspace-header__stat {
  padding: 12px 14px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.72);
}

.workspace-header__stat span {
  display: block;
  font-size: 11px;
  color: #94a3b8;
}

.workspace-header__stat strong {
  display: block;
  margin-top: 8px;
  font-size: 20px;
  color: #f8fafc;
}

@media (max-width: 1200px) {
  .workspace-header {
    flex-direction: column;
    align-items: stretch;
  }

  .workspace-header__meta {
    min-width: 0;
  }
}
</style>
