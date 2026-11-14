<template>
  <!-- 外层容器：只要有选中的围栏就显示 -->
  <div class="edit-container" v-if="currentEditFence">
    <!-- 悬浮的控制按钮 -->
    <el-button
      class="toggle-btn"
      type="primary"
      @click="isCardVisible = !isCardVisible"
    >
      {{ isCardVisible ? "隐藏编辑面板" : "编辑当前围栏" }}
    </el-button>

    <!-- 实际的编辑卡片 -->
    <div class="edit-card" v-show="isCardVisible">
      <div class="card-header">
        <h3>编辑: {{ currentEditFence.id }}</h3>
        <el-button type="danger" link @click="closeEditCard">退出</el-button>
      </div>

      <el-form label-width="auto">
        <!-- 经纬度如果也想统一抽离，可以参考高度的写法。这里重点演示高度 -->
        <el-form-item label="统一高度">
          <!-- 使用 type="number" 限制输入，避免 NaN 错误 -->
          <el-input v-model="uniformHeight" type="number" />
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useEntityDataStore } from "@/stores/EntityData";

const entityDataStore = useEntityDataStore();

// 控制卡片显示隐藏的响应式变量
const isCardVisible = ref(true);

const currentEditFence = computed(() => entityDataStore.currentEditFence);

// 极致简化的计算属性
const uniformHeight = computed({
  get() {
    // 使用可选链操作符 (?.) 安全读取第一个点的高度作为展示
    return currentEditFence.value?.height ?? 0;
  },
  set(value: string | number) {
    const parsedHeight = parseFloat(value as string);
    if (!isNaN(parsedHeight)) {
      // 直接调用 Store 的方法，组件不关心具体怎么改
      entityDataStore.updateCurrentFenceHeight(parsedHeight);
    }
  },
});

const closeEditCard = () => {
  entityDataStore.setCurrentEditId(null);
  isCardVisible.value = true; // 退出时重置状态
};
</script>

<style scoped>
.edit-container {
  position: absolute;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  z-index: 999; /* 确保在地图上方 */
}

.toggle-btn {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.edit-card {
  width: 280px;
  background: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}
.card-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}
</style>
