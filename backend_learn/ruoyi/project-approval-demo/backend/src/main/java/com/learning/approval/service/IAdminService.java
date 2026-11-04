package com.learning.approval.service;

import com.learning.approval.common.PageResult;
import com.learning.approval.domain.*;
import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.security.CurrentUser;
import java.util.List;

public interface IAdminService {
    PageResult<AdminUserResponse> users(int page, int size);
    List<Organization> organizations();
    List<RoleResponse> roles();
    List<Permission> permissions();
    long createUser(CurrentUser actor, UserCreateRequest request);
    void assignRoles(CurrentUser actor, long userId, UserRolesRequest request);
    void setEnabled(CurrentUser actor, long userId, boolean enabled);
    void revokeUser(CurrentUser actor, long userId);
    void changeRolePermissions(long roleId, RolePermissionsRequest request);
    PageResult<AuditLog> auditLogs(int page, int size, String category);
}
