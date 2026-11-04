package com.learning.approval.domain;

import com.fasterxml.jackson.annotation.JsonIgnore;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/** 与业务一起提交的流转记录，页面不能修改。 */
public class ProjectEvent {

    /** 事件ID */
    private Long id;

    /** 材料ID */
    private String projectId;

    /** 轮次；草稿操作可空 */
    private Integer roundNo;

    /** 节点ID，可空 */
    private String stepId;

    /** 真实操作人 */
    private Long actorId;

    /** 操作人姓名快照 */
    private String actorName;

    /** 操作类型 */
    private String action;

    /** 说明 */
    private String note;

    /** 原状态 */
    private String beforeStatus;

    /** 新状态 */
    private String afterStatus;

    /** 原版本 */
    private Long beforeVersion;

    /** 新版本 */
    private Long afterVersion;

    /** 操作时间 */
    private LocalDateTime createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getProjectId() {
        return projectId;
    }

    public void setProjectId(String projectId) {
        this.projectId = projectId;
    }

    public Integer getRoundNo() {
        return roundNo;
    }

    public void setRoundNo(Integer roundNo) {
        this.roundNo = roundNo;
    }

    public String getStepId() {
        return stepId;
    }

    public void setStepId(String stepId) {
        this.stepId = stepId;
    }

    public Long getActorId() {
        return actorId;
    }

    public void setActorId(Long actorId) {
        this.actorId = actorId;
    }

    public String getActorName() {
        return actorName;
    }

    public void setActorName(String actorName) {
        this.actorName = actorName;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public String getNote() {
        return note;
    }

    public void setNote(String note) {
        this.note = note;
    }

    public String getBeforeStatus() {
        return beforeStatus;
    }

    public void setBeforeStatus(String beforeStatus) {
        this.beforeStatus = beforeStatus;
    }

    public String getAfterStatus() {
        return afterStatus;
    }

    public void setAfterStatus(String afterStatus) {
        this.afterStatus = afterStatus;
    }

    public Long getBeforeVersion() {
        return beforeVersion;
    }

    public void setBeforeVersion(Long beforeVersion) {
        this.beforeVersion = beforeVersion;
    }

    public Long getAfterVersion() {
        return afterVersion;
    }

    public void setAfterVersion(Long afterVersion) {
        this.afterVersion = afterVersion;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
