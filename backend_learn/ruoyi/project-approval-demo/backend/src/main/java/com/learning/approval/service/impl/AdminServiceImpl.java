package com.learning.approval.service.impl;

import static com.learning.approval.exception.BusinessException.require;

import com.learning.approval.common.PageResult;
import com.learning.approval.domain.*;
import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.mapper.*;
import com.learning.approval.security.*;
import com.learning.approval.service.IAdminService;
import java.util.*;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AdminServiceImpl implements IAdminService {

    private final UserMapper users;
    private final RoleMapper roles;
    private final AuditMapper audit;
    private final PasswordEncoder passwords;
    private final ApplicationEventPublisher events;

    public AdminServiceImpl(
        UserMapper users,
        RoleMapper roles,
        AuditMapper audit,
        PasswordEncoder passwords,
        ApplicationEventPublisher events
    ) {
        this.users = users;
        this.roles = roles;
        this.audit = audit;
        this.passwords = passwords;
        this.events = events;
    }

    private void page(int page, int size) {
        require(page >= 1 && page <= 100000 && size >= 1 && size <= 50, 400, "分页参数不合法");
    }

    @Override
    public PageResult<AdminUserResponse> users(int page, int size) {
        page(page, size);
        return new PageResult<>(
            users
                .selectUsers(size, (page - 1) * size)
                .stream()
                .map(u -> new AdminUserResponse(u, roles.selectUserRoleIds(u.getId())))
                .toList(),
            users.countUsers(),
            page,
            size
        );
    }

    @Override
    public List<Organization> organizations() {
        return users.selectOrganizations();
    }

    @Override
    public List<RoleResponse> roles() {
        return roles
            .selectRoles()
            .stream()
            .map(r -> new RoleResponse(r, roles.selectRolePermissions(r.getId())))
            .toList();
    }

    @Override
    public List<Permission> permissions() {
        return roles.selectPermissions();
    }

    private void validateRoles(CurrentUser actor, List<Long> roleIds) {
        require(new HashSet<>(roleIds).size() == roleIds.size(), 400, "角色不能重复");
        for (Long id : roleIds) {
            Role role = roles.selectRole(id);
            require(
                role != null && Boolean.TRUE.equals(role.getEnabled()),
                400,
                "角色不存在或已停用"
            );
            // 获得“分配普通业务角色”权限，不等于可以创建新的系统管理员。
            require(
                actor.hasPermission("system:role:edit") ||
                    roles
                        .selectRolePermissions(id)
                        .stream()
                        .noneMatch(code -> code.startsWith("system:")),
                403,
                "分配管理权限需要角色权限管理权"
            );
        }
    }

    @Override
    @Transactional
    public long createUser(CurrentUser actor, UserCreateRequest request) {
        validateRoles(actor, request.roleIds());
        AuthServiceImpl.validateNewPassword(request.password());
        require(users.selectOrganization(request.orgId()) != null, 400, "组织不存在");
        long id = users.lockNextUserId();
        users.advanceUserId();
        AppUser user = new AppUser();
        user.setId(id);
        user.setUsername(request.username());
        user.setDisplayName(request.displayName().strip());
        user.setPasswordHash(passwords.encode(request.password()));
        user.setOrgId(request.orgId());
        user.setEnabled(true);
        users.insertUser(user);
        users.insertSecurity(id);
        for (Long role : request.roleIds()) roles.insertUserRole(id, role);
        return id;
    }

    private AppUser editableUser(CurrentUser actor, long userId) {
        require(actor.id() != userId, 409, "不能修改自己的角色或停用自己，请使用其他管理账号");
        require(users.lockSecurityStamp(userId) != null, 404, "用户不存在");
        AppUser target = users.selectById(userId);
        require(
            !"admin".equalsIgnoreCase(target.getUsername()),
            409,
            "内置管理员账号的角色和启用状态保持固定"
        );
        require(
            actor.hasPermission("system:role:edit") ||
                roles
                    .selectUserPermissions(userId)
                    .stream()
                    .noneMatch(code -> code.startsWith("system:")),
            403,
            "修改管理身份需要角色权限管理权"
        );
        return target;
    }

    @Override
    @Transactional
    public void assignRoles(CurrentUser actor, long userId, UserRolesRequest request) {
        editableUser(actor, userId);
        validateRoles(actor, request.roleIds());
        roles.deleteUserRoles(userId);
        for (Long role : request.roleIds()) roles.insertUserRole(userId, role);
        users.incrementAuthVersion(userId);
        events.publishEvent(new SessionRevocationEvent(List.of(userId)));
    }

    @Override
    @Transactional
    public void setEnabled(CurrentUser actor, long userId, boolean enabled) {
        editableUser(actor, userId);
        users.updateEnabled(userId, enabled);
        users.incrementAuthVersion(userId);
        events.publishEvent(new SessionRevocationEvent(List.of(userId)));
    }

    @Override
    @Transactional
    public void revokeUser(CurrentUser actor, long userId) {
        require(users.lockSecurityStamp(userId) != null, 404, "用户不存在");
        require(
            actor.hasPermission("system:role:edit") ||
                roles
                    .selectUserPermissions(userId)
                    .stream()
                    .noneMatch(code -> code.startsWith("system:")),
            403,
            "撤销管理身份的会话需要角色权限管理权"
        );
        users.incrementAuthVersion(userId);
        events.publishEvent(new SessionRevocationEvent(List.of(userId)));
    }

    @Override
    @Transactional
    public void changeRolePermissions(long roleId, RolePermissionsRequest request) {
        Role role = roles.selectRole(roleId);
        require(role != null, 404, "角色不存在");
        require(
            !Boolean.TRUE.equals(role.getBuiltIn()),
            409,
            "内置管理角色的权限不可通过此接口修改"
        );
        Set<String> allowed = new HashSet<>();
        roles.selectPermissions().forEach(p -> allowed.add(p.getCode()));
        require(
            new HashSet<>(request.permissions()).size() == request.permissions().size() &&
                allowed.containsAll(request.permissions()),
            400,
            "权限标识重复或不存在"
        );
        List<Long> affected = roles.selectRoleUserIds(roleId);
        roles.deleteRolePermissions(roleId);
        for (String code : request.permissions()) roles.insertRolePermission(roleId, code);
        roles.incrementRoleUserVersions(roleId);
        events.publishEvent(new SessionRevocationEvent(affected));
    }

    @Override
    public PageResult<AuditLog> auditLogs(int page, int size, String category) {
        page(page, size);
        require(
            category == null ||
                category.isEmpty() ||
                Set.of("AUTH", "BUSINESS", "ADMIN").contains(category),
            400,
            "日志类型不合法"
        );
        return new PageResult<>(
            audit.select(category, size, (page - 1) * size),
            audit.count(category),
            page,
            size
        );
    }
}
