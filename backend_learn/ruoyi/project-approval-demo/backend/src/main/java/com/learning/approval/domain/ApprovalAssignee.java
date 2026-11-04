package com.learning.approval.domain;

import com.fasterxml.jackson.annotation.JsonIgnore;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/** 候选审批人及其任务状态。 */
public class ApprovalAssignee {

    /** 节点ID */
    private String stepId;

    /** 候选人ID */
    private Long userId;

    /** 账号快照 */
    private String username;

    /** 姓名快照 */
    private String displayName;

    /** WAITING/PENDING/PASSED/REJECTED/CLOSED/CANCELLED */
    private String status;

    public String getStepId() {
        return stepId;
    }

    public void setStepId(String stepId) {
        this.stepId = stepId;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
