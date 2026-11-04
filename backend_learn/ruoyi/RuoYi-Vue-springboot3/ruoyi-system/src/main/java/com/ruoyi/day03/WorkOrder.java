package com.ruoyi.day03;

public class WorkOrder {

    private Long id;
    private String title;
    private String status;

    public WorkOrder(Long id, String title) {
        this.id = id;
        this.title = title;
        this.status = "DRAFT";
    }

    public Long getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public String getStatus() {
        return status;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    // 仅同一个包内的代码可以直接调用
    void markSubmitted() {
        this.status = "SUBMITTED";
    }

    @Override
    public String toString() {
        return "WorkOrder{id=" + id
                + ", title='" + title + '\''
                + ", status='" + status + '\'' + '}';
    }
}