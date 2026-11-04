package com.ruoyi.system.domain.practice;

public class WorkOrder {
    private Long id;
    private String title;
    private int status;

    public WorkOrder(Long id, String title, int status){
        this.id=id;
        this.title=title;
        this.status=status;
    }
    public boolean submit(){
        if(this.status!=0){
            return false;
        }
        this.status=1;
        return true;
    }

    public String summary() {
        return "工单 " + id + "：" + title
                + "，状态=" + status;
    }

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
