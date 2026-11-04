package com.learning.approval.dto.response;

import com.learning.approval.domain.AppUser;
import java.util.List;

public record AdminUserResponse(AppUser user, List<Long> roleIds) {}
