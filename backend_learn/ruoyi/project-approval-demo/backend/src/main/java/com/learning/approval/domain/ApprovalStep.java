package com.learning.approval.domain;

import com.fasterxml.jackson.annotation.JsonIgnore;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/** 一个审批单位对应一个或签节点，路径在提交时冻结。 */
public class ApprovalStep {

    /** 节点UUID */
    private String id;

    /** 材料ID */
    private String projectId;

    /** 轮次 */
    private Integer roundNo;

    /** 节点顺序 */
    private Integer seq;

    /** 审批单位ID */
    private Long orgId;

    /** 审批单位名称 */
    private String orgName;

    /** WAITING/PENDING/PASSED/REJECTED/CANCELLED */
    private String status;

    /** 实际办理人 */
    private Long actorId;

    /** 实际办理人姓名 */
    private String actorName;

    /** 意见 */
    private String opinion;

    /** 节点激活时间，未流转到的节点为空 */
    private LocalDateTime startedAt;

    /** 办理时间 */
    private LocalDateTime actedAt;

    public String getId() {
        return id;
    }

    public void setId(String id) {
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

    public Integer getSeq() {
        return seq;
    }

    public void setSeq(Integer seq) {
        this.seq = seq;
    }

    public Long getOrgId() {
        return orgId;
    }

    public void setOrgId(Long orgId) {
        this.orgId = orgId;
    }

    public String getOrgName() {
        return orgName;
    }

    public void setOrgName(String orgName) {
        this.orgName = orgName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
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

    public String getOpinion() {
        return opinion;
    }

    public void setOpinion(String opinion) {
        this.opinion = opinion;
    }

    public LocalDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(LocalDateTime startedAt) {
        this.startedAt = startedAt;
    }

    public LocalDateTime getActedAt() {
        return actedAt;
    }

    public void setActedAt(LocalDateTime actedAt) {
        this.actedAt = actedAt;
    }
}
