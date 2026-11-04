package com.learning.approval.mapper;

import com.learning.approval.domain.*;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface RoleMapper {
    List<String> selectUserRoles(Long userId);
    List<String> selectUserPermissions(Long userId);
    List<Long> selectUserRoleIds(Long userId);
    List<Role> selectRoles();
    Role selectRole(Long roleId);
    List<Permission> selectPermissions();
    List<String> selectRolePermissions(Long roleId);
    int deleteUserRoles(Long userId);
    int insertUserRole(@Param("userId") Long userId, @Param("roleId") Long roleId);
    int deleteRolePermissions(Long roleId);
    int insertRolePermission(@Param("roleId") Long roleId, @Param("permission") String permission);
    List<Long> selectRoleUserIds(Long roleId);
    int incrementRoleUserVersions(Long roleId);
    List<AppUser> selectReviewers(
        @Param("orgId") Long orgId,
        @Param("excludeUserId") Long excludeUserId
    );
}
