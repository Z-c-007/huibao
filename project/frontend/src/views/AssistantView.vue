<script setup lang="ts">
import ChatPanel from '../components/ChatPanel.vue'
</script>

<template>
  <div class="assistant-page">
    <div class="chat-frame">
      <ChatPanel />
    </div>
  </div>
</template>

<style scoped>
.assistant-page {
  height: 100%;
  display: flex;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}
.chat-frame {
  width: 860px;
  max-width: 100%;
  height: 100%;
  border: 1px solid #f0f0f0;
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
}
</style>
