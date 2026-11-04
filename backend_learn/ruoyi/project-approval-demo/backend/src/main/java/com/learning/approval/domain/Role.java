package com.learning.approval.domain;

import com.fasterxml.jackson.annotation.JsonIgnore;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/** 可配置角色；业务逻辑不按角色名称写死判断。 */
public class Role {

    /** 角色ID */
    private Long id;

    /** 角色编码 */
    private String code;

    /** 角色名 */
    private String name;

    /** 是否启用 */
    private Boolean enabled;

    /** 内置管理角色，不能编辑其权限 */
    private Boolean builtIn;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public Boolean getBuiltIn() {
        return builtIn;
    }

    public void setBuiltIn(Boolean builtIn) {
        this.builtIn = builtIn;
    }
}
