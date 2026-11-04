package com.learning.approval.domain;

import com.fasterxml.jackson.annotation.JsonIgnore;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/** 只读查询结果，关联组织、填报人及当前节点。 */
public class ProjectView extends Project {

    /** 建设单位 */
    private String orgName;

    /** 填报人姓名 */
    private String creatorName;

    /** 当前审批单位 */
    private String currentOrgName;

    /** 审核列表对应的轮次 */
    private Integer visibleRoundNo;

    public String getOrgName() {
        return orgName;
    }

    public void setOrgName(String orgName) {
        this.orgName = orgName;
    }

    public String getCreatorName() {
        return creatorName;
    }

    public void setCreatorName(String creatorName) {
        this.creatorName = creatorName;
    }

    public String getCurrentOrgName() {
        return currentOrgName;
    }

    public void setCurrentOrgName(String currentOrgName) {
        this.currentOrgName = currentOrgName;
    }

    public Integer getVisibleRoundNo() {
        return visibleRoundNo;
    }

    public void setVisibleRoundNo(Integer visibleRoundNo) {
        this.visibleRoundNo = visibleRoundNo;
    }
}
