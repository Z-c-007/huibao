import { defineStore } from "pinia";
import { computed, ref } from "vue";
import type { ElectronicFenceOptions } from "../types/index.ts";
export const useEntityDataStore = defineStore("EntityData", () => {
  const electronicFences = ref<ElectronicFenceOptions[]>([]);
  const currentEditId = ref<string | null>(null);
  const currentEditFence = computed(() => {
    return electronicFences.value.find(
      (fence) => fence.id === currentEditId.value,
    );
  });
  /**
   * 添加电子围栏数据
   * @param options
   */
  const addElectronicFence = (options: ElectronicFenceOptions) => {
    electronicFences.value.push(options);
  };
  /**
   * 设置电子围栏数据
   * @param fences
   */
  const setElectronicFences = (fences: ElectronicFenceOptions[]) => {
    electronicFences.value = fences;
  };
  /**
   * 更新电子围栏数据
   * @param options
   */
  const updateElectronicFence = (options: ElectronicFenceOptions[]) => {
    electronicFences.value = options;
  };

  /**
   * 清空电子围栏数据
   */
  const clearElectronicFences = () => {
    electronicFences.value = [];
  };

  const setCurrentEditId = (id: string | null) => {
    currentEditId.value = id;
  };
  // 统一更新当前编辑围栏的所有高度
  const updateCurrentFenceHeight = (newHeight: number) => {
    const fence = currentEditFence.value;
    if (!fence) return;

    fence.height = newHeight; // 更新围栏的统一高度属性

    // TODO: 如果这里需要触发地图引擎更新实体，可以通过事件总线或回调通知地图
  };
  return {
    electronicFences,
    addElectronicFence,
    setElectronicFences,
    clearElectronicFences,
    updateElectronicFence,
    currentEditId,
    currentEditFence,
    setCurrentEditId,
    updateCurrentFenceHeight,
  };
});
