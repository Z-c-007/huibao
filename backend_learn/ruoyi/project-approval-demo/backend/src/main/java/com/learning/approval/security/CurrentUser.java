package com.learning.approval.security;

import java.util.List;

/** 当前用户的安全视图，不含密码。permissions来自数据库角色关联，不由前端指定。 */
public record CurrentUser(
    long id,
    String username,
    String displayName,
    long orgId,
    String orgName,
    List<String> roles,
    List<String> permissions,
    long authVersion
) {
    public boolean hasPermission(String code) {
        return permissions.contains(code);
    }
}
