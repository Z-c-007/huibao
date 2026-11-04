package com.learning.approval.controller;

import com.learning.approval.audit.AuditAction;
import com.learning.approval.common.*;
import com.learning.approval.domain.*;
import com.learning.approval.dto.request.*;
import com.learning.approval.dto.response.*;
import com.learning.approval.security.CurrentUser;
import com.learning.approval.service.IAdminService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@Validated
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final IAdminService service;

    public AdminController(IAdminService service) {
        this.service = service;
    }

    @GetMapping("/users")
    @PreAuthorize("hasAuthority('system:user:list')")
    public ApiResponse<PageResult<AdminUserResponse>> users(
        @RequestParam(defaultValue = "1") @Min(1) int page,
        @RequestParam(defaultValue = "10") @Min(1) @Max(50) int size
    ) {
        return ApiResponse.success(service.users(page, size));
    }

    @GetMapping("/organizations")
    @PreAuthorize("hasAnyAuthority('system:user:list','system:user:create')")
    public ApiResponse<List<Organization>> organizations() {
        return ApiResponse.success(service.organizations());
    }

    @GetMapping("/roles")
    @PreAuthorize("hasAuthority('system:role:list')")
    public ApiResponse<List<RoleResponse>> roles() {
        return ApiResponse.success(service.roles());
    }

    @GetMapping("/permissions")
    @PreAuthorize("hasAuthority('system:role:list')")
    public ApiResponse<List<Permission>> permissions() {
        return ApiResponse.success(service.permissions());
    }

    @PostMapping("/users")
    @PreAuthorize("hasAuthority('system:user:create') and hasAuthority('system:user:assign')")
    @AuditAction(value = "CREATE_USER", category = "ADMIN")
    public ApiResponse<Long> create(
        @AuthenticationPrincipal CurrentUser user,
        @Valid @RequestBody UserCreateRequest body
    ) {
        return ApiResponse.success(service.createUser(user, body));
    }

    @PutMapping("/users/{id}/roles")
    @PreAuthorize("hasAuthority('system:user:assign')")
    @AuditAction(value = "ASSIGN_USER_ROLES", category = "ADMIN")
    public ApiResponse<Boolean> assign(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable @Positive Long id,
        @Valid @RequestBody UserRolesRequest body
    ) {
        service.assignRoles(user, id, body);
        return ApiResponse.success(true);
    }

    @PutMapping("/users/{id}/enabled")
    @PreAuthorize("hasAuthority('system:user:disable')")
    @AuditAction(value = "CHANGE_USER_STATUS", category = "ADMIN")
    public ApiResponse<Boolean> enabled(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable @Positive Long id,
        @RequestParam boolean enabled
    ) {
        service.setEnabled(user, id, enabled);
        return ApiResponse.success(true);
    }

    @DeleteMapping("/users/{id}/sessions")
    @PreAuthorize("hasAuthority('system:user:revoke')")
    @AuditAction(value = "REVOKE_USER_SESSIONS", category = "ADMIN")
    public ApiResponse<Boolean> revoke(
        @AuthenticationPrincipal CurrentUser user,
        @PathVariable @Positive Long id
    ) {
        service.revokeUser(user, id);
        return ApiResponse.success(true);
    }

    @PutMapping("/roles/{id}/permissions")
    @PreAuthorize("hasAuthority('system:role:edit')")
    @AuditAction(value = "CHANGE_ROLE_PERMISSIONS", category = "ADMIN")
    public ApiResponse<Boolean> permissions(
        @PathVariable @Positive Long id,
        @Valid @RequestBody RolePermissionsRequest body
    ) {
        service.changeRolePermissions(id, body);
        return ApiResponse.success(true);
    }

    @GetMapping("/audit-logs")
    @PreAuthorize("hasAuthority('system:audit:list')")
    public ApiResponse<PageResult<AuditLog>> logs(
        @RequestParam(defaultValue = "1") @Min(1) int page,
        @RequestParam(defaultValue = "10") @Min(1) @Max(50) int size,
        @RequestParam(defaultValue = "") String category
    ) {
        return ApiResponse.success(service.auditLogs(page, size, category));
    }
}
