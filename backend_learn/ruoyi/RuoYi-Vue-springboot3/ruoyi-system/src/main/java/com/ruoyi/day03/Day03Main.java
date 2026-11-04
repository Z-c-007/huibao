package com.ruoyi.day03;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class Day03Main {

    public static void main(String[] args) {

        // 1. 手动创建实现类对象
        WorkOrderService service = new WorkOrderServiceImpl();

        // 2. 新增工单
        service.add(new WorkOrder(1001L, "水泵巡检"));
        service.add(new WorkOrder(1002L, "闸门巡检"));

        // 3. 查询列表
        System.out.println("全部工单：" + service.list());

        // 4. 查询单条工单
        System.out.println("查询工单：" + service.findById(1001L));

        // 5. 验证业务规则
        System.out.println("第一次提交：" + service.submit(1001L));
        System.out.println("第二次提交：" + service.submit(1001L));
        System.out.println("提交后工单：" + service.findById(1001L));
        System.out.println("不存在的工单提交：" + service.submit(9999L));

        // 6. List：允许重复，保留列表顺序
        List<String> list = new ArrayList<>();
        list.add("水泵巡检");
        list.add("水泵巡检");
        list.add("闸门巡检");

        System.out.println("List 数量：" + list.size());
        System.out.println("List 内容：" + list);

        // 7. Set：不保留重复元素
        Set<String> set = new HashSet<>();
        set.add("水泵巡检");
        set.add("水泵巡检");
        set.add("闸门巡检");

        System.out.println("Set 数量：" + set.size());
        System.out.println("Set 内容：" + set);

        // 8. Map：通过键查找值
        Map<Long, String> map = new HashMap<>();
        map.put(1001L, "水泵巡检");
        map.put(1001L, "更新后的水泵巡检");
        map.put(1002L, "闸门巡检");

        System.out.println("Map 数量：" + map.size());
        System.out.println("工单 1001：" + map.get(1001L));
        System.out.println("Map 内容：" + map);
    }
}