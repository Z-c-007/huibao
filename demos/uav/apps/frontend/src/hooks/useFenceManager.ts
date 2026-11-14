import * as Cesium from "cesium";
import { useEntityDataStore } from "@/stores/EntityData";
import { watch, onUnmounted } from "vue";
import { createElectronicFence } from "@/utils/DrawObstacle/createGroundPrimitive";

export function useFenceManager(viewer: Cesium.Viewer) {
  const entityDataStore = useEntityDataStore();

  const fenceCache = new Map<string, any>(); //维护一个字典，记录 Store 中的 id 对应的 Cesium Primitive 实例
  const stopWatch = watch(
    () => entityDataStore.electronicFences,
    (newFences) => {
      // 记录当前 store 中存在的 ID
      const currentStoreIds = new Set(newFences.map((f) => f.id));
      // A. 清理已经被删除的围栏
      for (const [id, primitive] of fenceCache.entries()) {
        if (!currentStoreIds.has(id)) {
          primitive.instance.destroy();
          fenceCache.delete(id);
        }
      }

      // B. 新增或更新围栏
      newFences.forEach((fenceData) => {
        // 因为深层属性（如高度）修改时也会触发这个 watch
        // 对于 Primitive，我们需要先移除旧的，再绘制新的
        if (fenceCache.has(fenceData.id)) {
          const oldFenceResult = fenceCache.get(fenceData.id);
          // 调用类的实例自带的 destroy 方法，把它内部的 Primitive 和 Entity 统统删干净
          oldFenceResult.instance.destroy();
        }
        const fencePrimitive = createElectronicFence(viewer, fenceData);
        fenceCache.set(fenceData.id, fencePrimitive);
      });
    },
    { deep: true },
  );
  // 2. 注册鼠标点击事件，实现“点击实体弹出编辑卡片”
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction(
    (click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const pickedObject = viewer.scene.pick(click.position);
      if (Cesium.defined(pickedObject)) {
        const entityId = pickedObject.id;
        entityDataStore.setCurrentEditId(entityId); // 将点击的实体 ID 存入 Store，触发编辑卡片显示
      } else {
        entityDataStore.setCurrentEditId(null); // 点击空白处，关闭编辑卡片
      }
    },
    Cesium.ScreenSpaceEventType.LEFT_CLICK,
  );
  // 3. 组件卸载时，清理监听和事件
  onUnmounted(() => {
    stopWatch(); // 停止监听
    handler.destroy(); // 销毁鼠标事件
    // 清空地图上的围栏
    for (const primitive of fenceCache.values()) {
      primitive.instance.destroy();
    }
    fenceCache.clear();
  });
}
