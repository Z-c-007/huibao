package com.learning.approval.domain;

import com.fasterxml.jackson.annotation.JsonIgnore;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/** 不可覆盖的提交轮次与材料快照；旧版本没有保存的快照明确标记不可用。 */
public class Submission {

    /** 提交UUID */
    private String id;

    /** 材料ID */
    private String projectId;

    /** 轮次 */
    private Integer roundNo;

    /** 提交人 */
    private Long submitterId;

    /** 提交人姓名快照 */
    private String submitterName;

    /** 组织ID快照 */
    private Long orgId;

    /** 组织名快照 */
    private String orgName;

    /** 编号快照 */
    private String projectCode;

    /** 名称快照 */
    private String projectName;

    /** 金额快照 */
    private BigDecimal amount;

    /** 材料快照 */
    private String material;

    /** PENDING/APPROVED/REJECTED/CANCELLED */
    private String status;

    /** 快照是否真实存在；升级前的轮次为false */
    private Boolean snapshotAvailable;

    /** 提交请求幂等键 */
    @JsonIgnore
    private String idempotencyKey;

    /** 请求参数摘要 */
    @JsonIgnore
    private String requestHash;

    /** 提交时间；旧版本未知则为空 */
    private LocalDateTime submittedAt;

    /** 结束时间 */
    private LocalDateTime closedAt;

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

    public Long getSubmitterId() {
        return submitterId;
    }

    public void setSubmitterId(Long submitterId) {
        this.submitterId = submitterId;
    }

    public String getSubmitterName() {
        return submitterName;
    }

    public void setSubmitterName(String submitterName) {
        this.submitterName = submitterName;
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

    public String getProjectCode() {
        return projectCode;
    }

    public void setProjectCode(String projectCode) {
        this.projectCode = projectCode;
    }

    public String getProjectName() {
        return projectName;
    }

    public void setProjectName(String projectName) {
        this.projectName = projectName;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public String getMaterial() {
        return material;
    }

    public void setMaterial(String material) {
        this.material = material;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Boolean getSnapshotAvailable() {
        return snapshotAvailable;
    }

    public void setSnapshotAvailable(Boolean snapshotAvailable) {
        this.snapshotAvailable = snapshotAvailable;
    }

    public String getIdempotencyKey() {
        return idempotencyKey;
    }

    public void setIdempotencyKey(String idempotencyKey) {
        this.idempotencyKey = idempotencyKey;
    }

    public String getRequestHash() {
        return requestHash;
    }

    public void setRequestHash(String requestHash) {
        this.requestHash = requestHash;
    }

    public LocalDateTime getSubmittedAt() {
        return submittedAt;
    }

    public void setSubmittedAt(LocalDateTime submittedAt) {
        this.submittedAt = submittedAt;
    }

    public LocalDateTime getClosedAt() {
        return closedAt;
    }

    public void setClosedAt(LocalDateTime closedAt) {
        this.closedAt = closedAt;
    }
}
