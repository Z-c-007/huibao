package com.learning.approval.mapper;

import com.learning.approval.domain.*;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface UserMapper {
    AppUser selectByUsername(String username);
    AppUser selectById(Long id);
    SecurityStamp selectSecurityStamp(Long userId);
    SecurityStamp lockSecurityStamp(Long userId);
    List<AppUser> selectUsers(@Param("limit") int limit, @Param("offset") int offset);
    long countUsers();
    long lockNextUserId();
    int advanceUserId();
    int insertUser(AppUser user);
    int insertSecurity(Long userId);
    int updatePassword(@Param("userId") Long userId, @Param("hash") String hash);
    int incrementAuthVersion(Long userId);
    int updateEnabled(@Param("userId") Long userId, @Param("enabled") boolean enabled);
    List<Organization> selectOrganizations();
    Organization selectOrganization(Long id);
}
