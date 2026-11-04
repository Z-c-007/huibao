package com.ruoyi.system.domain.practice;

public class WorkOrderDemo {
    public static void main(String[] args) {
        WorkOrder[] orders = {
                new WorkOrder(1001L, "东区2号水泵巡检", 0),
                new WorkOrder(1002L, "东区阀门巡检", 1),
                new WorkOrder(1003L, "西区水泵巡检", 0)
        };
        int successCount = 0;
        for (WorkOrder order : orders) {

            // 4. 尝试提交当前工单
            boolean success = order.submit();

            // 5. 统计提交成功的数量
            if (success) {
                successCount++;
            }

            // 6. 输出当前工单信息
            System.out.println(
                    order.summary() + "，本次提交=" + success
            );
        }
        System.out.println("成功提交数量=" + successCount);

        // 8. 练习 Long 与 null
        Long emptyId = null;
        System.out.println("emptyId 是否为空：" + (emptyId == null));
    }
}
