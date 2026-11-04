package com.learning.approval.domain;

import com.fasterxml.jackson.annotation.JsonIgnore;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/** 每次请求核对的轻量状态，权限更新后旧会话立即失效。 */
public class SecurityStamp {

    /** 用户ID */
    private Long userId;

    /** 权限/密码版本 */
    private Long authVersion;

    /** 用户状态 */
    private Boolean enabled;

    /** 当前组织ID */
    private Long orgId;

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public Long getAuthVersion() {
        return authVersion;
    }

    public void setAuthVersion(Long authVersion) {
        this.authVersion = authVersion;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public Long getOrgId() {
        return orgId;
    }

    public void setOrgId(Long orgId) {
        this.orgId = orgId;
    }
}
