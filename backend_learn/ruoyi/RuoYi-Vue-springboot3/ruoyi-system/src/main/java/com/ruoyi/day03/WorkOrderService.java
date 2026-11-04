package com.ruoyi.day03;

import java.util.List;

public interface WorkOrderService {

    // 新增工单
    void add(WorkOrder workOrder);

    // 查询所有工单
    List<WorkOrder> list();

    // 根据 ID 查询工单
    WorkOrder findById(Long id);

    // 提交工单，返回是否成功
    boolean submit(Long id);
}