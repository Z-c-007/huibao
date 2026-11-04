
package com.ruoyi.system.domain.practice;

public class PracticeWorkOrder {

    // 1. 字段：保存工单数据
    private Long id;
    private String title;
    private int status;

    // 2. 构造器：创建对象时初始化字段
    public PracticeWorkOrder(Long id, String title, int status) {
        this.id = id;
        this.title = title;
        this.status = status;
    }

    // 3. 方法：尝试提交工单
    public boolean submit() {
        if (status != 0) {
            return false;
        }

        this.status = 1;
        return true;
    }

    // 4. 方法：生成工单描述
    public String summary() {
        return "工单 " + id + "：" + title
                + "，状态=" + status;
    }

    // 5. Getter：让外部读取字段
    public Long getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public int getStatus() {
        return status;
    }
}
