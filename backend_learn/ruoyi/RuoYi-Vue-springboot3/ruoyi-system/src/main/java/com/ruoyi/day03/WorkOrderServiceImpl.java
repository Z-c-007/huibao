package com.ruoyi.day03;

import java.util.ArrayList;
import java.util.List;

public class WorkOrderServiceImpl implements WorkOrderService {

    // 接口类型 List，具体创建 ArrayList 对象
    private final List<WorkOrder> workOrders = new ArrayList<>();

    @Override
    public void add(WorkOrder workOrder) {
        if (workOrder == null || workOrder.getId() == null) {
            throw new IllegalArgumentException("工单和工单 ID 不能为空");
        }

        if (findById(workOrder.getId()) != null) {
            throw new IllegalArgumentException(
                    "工单 ID 已存在：" + workOrder.getId());
        }

        workOrders.add(workOrder);
    }

    @Override
    public List<WorkOrder> list() {
        // 返回一个新的列表，避免调用方直接清空内部列表
        return new ArrayList<>(workOrders);
    }

    @Override
    public WorkOrder findById(Long id) {
        if (id == null) {
            return null;
        }

        for (WorkOrder workOrder : workOrders) {
            if (id.equals(workOrder.getId())) {
                return workOrder;
            }
        }

        return null;
    }

    @Override
    public boolean submit(Long id) {
        WorkOrder workOrder = findById(id);

        // 只有存在且处于草稿状态，才允许提交
        if (workOrder == null
                || !"DRAFT".equals(workOrder.getStatus())) {
            return false;
        }

        workOrder.markSubmitted();
        return true;
    }
}