<template>
  <div class="dashboard-layout">
    <div class="dashboard-layout__header">
      <slot name="header" />
    </div>

    <div class="dashboard-layout__body">
      <aside class="dashboard-layout__aside">
        <slot name="left" />
      </aside>

      <main class="dashboard-layout__main">
        <slot />
      </main>

      <aside class="dashboard-layout__aside">
        <slot name="right" />
      </aside>
    </div>

    <div class="dashboard-layout__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.dashboard-layout {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 16px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.dashboard-layout__body {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 320px;
  gap: 16px;
  min-height: 0;
  overflow: hidden;
}

.dashboard-layout__aside,
.dashboard-layout__main {
  min-height: 0;
  overflow: hidden;
}

.dashboard-layout__aside {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dashboard-layout__main {
  min-width: 0;
  display: flex;
}

.dashboard-layout__main > * {
  flex: 1;
  min-height: 0;
}

/* @media (max-width: 1400px) {
  .dashboard-layout__body {
    grid-template-columns: 280px minmax(0, 1fr) 280px;
  }
}

@media (max-width: 1180px) {
  .dashboard-layout__body {
    grid-template-columns: 1fr;
  }
} */
</style>
