<template>
  <footer class="workspace-footer">
    <div
      v-for="item in items"
      :key="item.label"
      class="workspace-footer__item"
    >
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
    </div>
  </footer>
</template>

<script setup lang="ts">
interface FooterItem {
  label: string;
  value: string;
}

defineProps<{
  items: FooterItem[];
}>();
</script>

<style scoped>
.workspace-footer {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 12px;
}

.workspace-footer__item {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.workspace-footer__item span {
  display: block;
  font-size: 11px;
  color: #94a3b8;
}

.workspace-footer__item strong {
  display: block;
  margin-top: 8px;
  font-size: 18px;
  color: #f8fafc;
}

@media (max-width: 960px) {
  .workspace-footer {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}
</style>
